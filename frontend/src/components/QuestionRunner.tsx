import { useMemo, useRef, useState } from "react";

import { ApiError } from "../api/client";
import { useAnswer } from "../api/hooks";
import type { Question, TaskResponse, TaskType } from "../api/types";
import { useExamTimer } from "../hooks/useExamTimer";
import { useRecorder } from "../hooks/useRecorder";
import { useSpeech } from "../hooks/useSpeech";
import { TASKS, WRITING_TYPES, phasesFor } from "../tasks";
import type { Stage } from "../tasks/types";
import { ResultPanel } from "./ResultPanel";
import styles from "./Runner.module.css";
import { TimerStrip } from "./TimerStrip";

interface Props {
  type: TaskType;
  question: Question;
  isLast: boolean;
  onNext: () => void;
}

/** Runs one question: audio, preparation and answer timing, recording, submission and the marked result. */
export function QuestionRunner({ type, question, isLast, onNext }: Props) {
  const Task = TASKS[type.code];
  const phases = useMemo(() => phasesFor(type), [type]);
  const review = question.answered;

  const speech = useSpeech();
  const recorder = useRecorder();
  const answer = useAnswer(question.set_id, question.position);

  const [response, setResponse] = useState<TaskResponse>(question.response ?? {});
  const [timeUp, setTimeUp] = useState(false);
  const responseRef = useRef(response);
  responseRef.current = response;
  const advanceRef = useRef<() => void>(() => {});

  const submit = (override?: TaskResponse) => {
    if (review || answer.isPending) return;
    let payload = override ?? responseRef.current;
    if (type.spoken) {
      const transcript = recorder.recording ? recorder.stop() : recorder.transcript;
      payload = { transcript: transcript || payload.transcript || "", self_rating: payload.self_rating };
    }
    answer.mutate(payload);
  };

  const timer = useExamTimer(phases, {
    autoStart: !review,
    onPhaseStart: (phase) => {
      if (phase.id === "audio") {
        const script = question.display.turns ?? question.display.audio ?? "";
        speech.play(script, () => advanceRef.current());
      }
      if (phase.id === "answer" && type.spoken) void recorder.start();
    },
    onComplete: () => {
      speech.stop();
      if (type.spoken) {
        const transcript = recorder.stop();
        setResponse((r) => ({ ...r, transcript }));
      } else {
        setTimeUp(true);
        if (!WRITING_TYPES.has(type.code)) submit();
      }
    },
  });
  advanceRef.current = timer.advance;

  const stage: Stage = review || timer.done ? "done" : (timer.phase?.id ?? "done");
  const locked = review || answer.isPending || (!type.spoken && timeUp);

  const spokenReady = () => {
    if (!type.spoken) return true;
    const transcript = (recorder.transcript || response.transcript || "").trim();
    if (transcript) return true;
    const rating = response.self_rating ?? {};
    return type.code === "ASQ" ? rating.correct !== undefined : rating.content !== undefined;
  };

  const canSubmit =
    !review &&
    !answer.isPending &&
    (type.spoken ? stage === "done" && spokenReady() : stage === "answer" || stage === "done" || (!type.audio && stage === "prep"));

  return (
    <div>
      {!review && <TimerStrip phase={timer.phase} remaining={timer.remaining} finishedLabel={type.spoken ? "Recording finished" : "Time's up"} />}

      <Task
        type={type}
        question={answer.data ?? question}
        response={response}
        onChange={setResponse}
        locked={locked}
        review={review}
        stage={stage}
        speaking={speech.speaking}
        recorder={type.spoken ? recorder : undefined}
      />

      {answer.error && <p className={styles.error}>{(answer.error as ApiError).message}</p>}

      {!review && (
        <div className={styles.actions}>
          {type.spoken && stage === "prep" && (
            <button type="button" className={styles.secondary} onClick={timer.advance}>
              Start recording now
            </button>
          )}
          {type.spoken && stage === "answer" && (
            <button type="button" className={styles.primary} onClick={timer.finish}>
              Stop recording
            </button>
          )}
          {(!type.spoken || stage === "done") && (
            <button type="button" className={styles.primary} onClick={() => submit()} disabled={!canSubmit}>
              {answer.isPending ? "Marking…" : "Submit answer"}
            </button>
          )}
          {type.spoken && stage === "done" && !spokenReady() && (
            <span className={styles.muted}>Rate your answer above to continue.</span>
          )}
        </div>
      )}

      {review && (
        <>
          <ResultPanel question={question} type={type} />
          <div className={styles.actions}>
            <button type="button" className={styles.primary} onClick={onNext} autoFocus>
              {isLast ? "See my results" : "Next question"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
