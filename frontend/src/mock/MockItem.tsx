import { useEffect, useMemo, useRef, useState } from "react";

import { ApiError } from "../api/client";
import { useMockAnswer } from "../api/hooks";
import type { MockQuestion, TaskResponse, TaskType } from "../api/types";
import { formatSeconds, useExamTimer } from "../hooks/useExamTimer";
import { useRecorder } from "../hooks/useRecorder";
import { useSpeech } from "../hooks/useSpeech";
import { TASKS, WRITING_TYPES, phasesFor } from "../tasks";
import type { Stage } from "../tasks/types";
import styles from "./Mock.module.css";

interface Props {
  question: MockQuestion;
  type: TaskType;
  /** Seconds left on the clock that governs this item, from the server. */
  secondsRemaining: number | null;
  onMoved: (position: number) => void;
  onFinished: () => void;
  onExit: () => void;
  /** True inside the reading part, where students may revisit earlier questions. */
  canGoBack: boolean;
}

/**
 * One question inside a mock test. It runs the real exam sequence for the task type, records or
 * collects the answer, and moves on by itself when the time is up. No score is ever shown here.
 */
export function MockItem({ question, type, secondsRemaining, onMoved, onFinished, onExit, canGoBack }: Props) {
  const pooled = question.allow_back; // the reading part runs on one clock for the whole part
  const phases = useMemo(() => (pooled ? [] : phasesFor(type)), [pooled, type]);
  const speech = useSpeech();
  const recorder = useRecorder();
  const answer = useMockAnswer(question.set_id);

  const [response, setResponse] = useState<TaskResponse>(question.response ?? {});
  const responseRef = useRef(response);
  responseRef.current = response;
  const submitted = useRef(false);
  const advanceRef = useRef<() => void>(() => {});

  const submit = (options: { keepPosition?: boolean } = {}) => {
    if (submitted.current || answer.isPending) return;
    submitted.current = true;
    let payload = responseRef.current;
    if (type.spoken) {
      const transcript = recorder.recording ? recorder.stop() : recorder.transcript;
      payload = { transcript: transcript || payload.transcript || "", self_rating: payload.self_rating };
    }
    speech.stop();
    answer.mutate(
      { position: question.position, response: payload },
      {
        onSuccess: (ack) => {
          if (ack.finished) onFinished();
          else if (options.keepPosition) submitted.current = false;
          else if (ack.next_position) onMoved(ack.next_position);
        },
        onError: () => {
          submitted.current = false;
        },
      },
    );
  };

  const timer = useExamTimer(phases, {
    autoStart: !pooled,
    onPhaseStart: (phase) => {
      if (phase.id === "audio") {
        speech.play(question.display.turns ?? question.display.audio ?? "", () => advanceRef.current());
      }
      if (phase.id === "answer" && type.spoken) void recorder.start();
    },
    onComplete: () => {
      // The real test moves on by itself once the answer time ends.
      submit();
    },
  });
  advanceRef.current = timer.advance;

  // The server's clock is the one that counts. If it reaches zero, send whatever the student has.
  useEffect(() => {
    if (secondsRemaining === 0) submit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [secondsRemaining]);

  const stage: Stage = pooled ? "answer" : timer.done ? "done" : (timer.phase?.id ?? "done");
  const Task = TASKS[type.code];
  const locked = answer.isPending || (!pooled && stage === "done" && !type.spoken && !WRITING_TYPES.has(type.code));

  const itemClock = !pooled && timer.phase?.seconds != null ? timer.remaining : null;

  return (
    <div>
      {!pooled && (
        <div className={styles.instructions} aria-live="polite">
          <strong>{type.name}.</strong> {type.instructions}
          {itemClock !== null && (
            <span className={styles.saveNote}>
              {" "}
              {timer.phase?.label}: {formatSeconds(itemClock)}
            </span>
          )}
        </div>
      )}
      {pooled && (
        <div className={styles.instructions}>
          <strong>{type.name}.</strong> {type.instructions}
        </div>
      )}

      <Task
        type={type}
        question={{
          set_id: question.set_id,
          position: question.position,
          set_question_id: question.set_question_id,
          question_id: question.question_id,
          task_type: question.task_type,
          display: question.display,
          answered: false,
          response: null,
          result: null,
          answer: null,
          feedback: null,
        }}
        response={response}
        onChange={setResponse}
        locked={locked}
        review={false}
        stage={stage}
        speaking={speech.speaking}
        recorder={type.spoken ? recorder : undefined}
      />

      {answer.error && (
        <p style={{ color: "var(--red)", fontWeight: 600 }}>
          {(answer.error as ApiError).message} Your answer wasn't saved. Try Next again.
        </p>
      )}

      <div className={styles.footer}>
        <div className={styles.footerInner}>
          {canGoBack && (
            <button
              type="button"
              className={styles.secondary}
              onClick={() => {
                submit({ keepPosition: true });
                onMoved(question.position - 1);
              }}
              disabled={answer.isPending}
            >
              Previous
            </button>
          )}
          <button type="button" className={styles.quiet} onClick={onExit}>
            Save and exit
          </button>
          <span className={styles.spacer} />
          {type.spoken && stage === "answer" && (
            <button type="button" className={styles.secondary} onClick={timer.finish} disabled={answer.isPending}>
              Stop recording
            </button>
          )}
          {type.spoken && stage === "prep" && (
            <button type="button" className={styles.secondary} onClick={timer.advance}>
              Start recording now
            </button>
          )}
          <button type="button" className={styles.primary} onClick={() => submit()} disabled={answer.isPending}>
            {answer.isPending ? "Saving…" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}
