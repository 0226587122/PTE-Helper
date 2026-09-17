import type { Stage } from "../types";
import styles from "../Tasks.module.css";

interface Props {
  stage: Stage;
  speaking: boolean;
  label?: string;
}

/** Shows what the audio is doing. Audio plays automatically once, after a short lead-in, as in the real test. */
export function AudioPanel({ stage, speaking, label = "Audio" }: Props) {
  let status = "Audio finished";
  let hint = "The audio plays only once.";
  if (stage === "leadin") {
    status = "Get ready";
    hint = "The audio will start in a moment.";
  } else if (stage === "audio" || speaking) {
    status = "Playing…";
    hint = "Listen carefully. You can take notes.";
  }
  return (
    <div className={styles.panel} aria-live="polite">
      <div className={styles.audio}>
        <div className={speaking ? styles.audioIconActive : styles.audioIcon} aria-hidden>
          🔊
        </div>
        <div>
          <div className={styles.audioStatus}>
            {label}: {status}
          </div>
          <div className={styles.audioHint}>{hint}</div>
        </div>
      </div>
    </div>
  );
}
