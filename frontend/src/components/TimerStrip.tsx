import { formatSeconds, type TimerPhase } from "../hooks/useExamTimer";
import styles from "./Runner.module.css";

interface Props {
  phase: TimerPhase | null;
  remaining: number | null;
  finishedLabel: string;
}

/** The dark bar at the top of each question showing the current phase and time left. */
export function TimerStrip({ phase, remaining, finishedLabel }: Props) {
  const timed = phase?.seconds != null && remaining != null;
  const fraction = timed ? remaining! / phase!.seconds! : phase ? 1 : 0;
  const low = timed && remaining! <= 10 && phase!.id === "answer";
  return (
    <div className={styles.strip} role="timer" aria-live="off">
      <div className={styles.stripRow}>
        <span className={styles.stripLabel}>{phase ? phase.label : finishedLabel}</span>
        <span className={low ? styles.stripTimeLow : styles.stripTime} aria-label="Time left">
          {timed ? formatSeconds(remaining!) : phase ? "…" : "0:00"}
        </span>
      </div>
      <div className={styles.bar}>
        <div className={styles.barFill} style={{ width: `${Math.max(0, Math.min(1, fraction)) * 100}%` }} />
      </div>
    </div>
  );
}
