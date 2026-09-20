import { useEffect, useRef, useState } from "react";

import type { Blueprint } from "../api/types";
import { formatSeconds, useExamTimer } from "../hooks/useExamTimer";
import { useRecorder } from "../hooks/useRecorder";
import styles from "./Mock.module.css";

/**
 * The spoken introduction that opens the real test. It is not scored and is not sent to the server,
 * but it is timed the same way, so the test starts exactly as the real one does.
 */
export function PersonalIntroduction({
  blueprint,
  onDone,
}: {
  blueprint: Blueprint["personal_introduction"];
  onDone: () => void;
}) {
  const recorder = useRecorder();
  const [finished, setFinished] = useState(false);
  const started = useRef(false);

  const timer = useExamTimer(
    [
      { id: "prep", label: "Recording starts in", seconds: blueprint.prep_seconds },
      { id: "answer", label: "Recording", seconds: blueprint.record_seconds },
    ],
    {
      onPhaseStart: (phase) => {
        if (phase.id === "answer" && !started.current) {
          started.current = true;
          void recorder.start();
        }
      },
      onComplete: () => {
        recorder.stop();
        setFinished(true);
      },
    },
  );

  useEffect(() => () => void recorder.stop(), []);

  return (
    <div className={styles.card}>
      <h1>{blueprint.title}</h1>
      <p className={styles.saveNote}>This response is not scored. It does not count towards your practice score.</p>
      <p className={styles.prompt}>{blueprint.prompt}</p>
      <p aria-live="polite">
        <strong>
          {finished
            ? "Recording complete."
            : `${timer.phase?.label ?? ""}: ${formatSeconds(timer.remaining ?? 0)}`}
        </strong>
      </p>
      {recorder.transcript && <p className={styles.saveNote}>What we heard: {recorder.transcript}</p>}
      <div className={styles.checkRow}>
        {!finished && (
          <button type="button" className={styles.secondary} onClick={timer.finish}>
            {timer.phase?.id === "answer" ? "Stop recording" : "Skip"}
          </button>
        )}
        <button type="button" className={styles.primary} onClick={onDone}>
          Continue to Part 1
        </button>
      </div>
    </div>
  );
}
