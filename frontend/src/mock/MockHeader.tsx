import { formatSeconds } from "../hooks/useExamTimer";
import styles from "./Mock.module.css";

interface Props {
  partTitle: string;
  taskName?: string;
  position: number;
  total: number;
  /** Seconds left on the part clock, for parts that have one (reading). */
  sectionRemaining: number | null;
  /** Seconds left before this answer is due, from the server. */
  itemRemaining: number | null;
}

/** Part clocks run for half an hour, so they warn earlier than a clock for a single question. */
function clockClass(seconds: number | null, kind: "part" | "item") {
  if (seconds === null) return styles.clockValue;
  const [warn, critical] = kind === "part" ? [300, 60] : [30, 10];
  if (seconds <= critical) return styles.clockCritical;
  if (seconds <= warn) return styles.clockWarn;
  return styles.clockValue;
}

/** The exam header: which part you're in, which question, and the clocks. */
export function MockHeader({ partTitle, taskName, position, total, sectionRemaining, itemRemaining }: Props) {
  // Announce the big milestones for screen readers without chattering every second.
  const announce =
    sectionRemaining === 300 || sectionRemaining === 60 || sectionRemaining === 10
      ? `${formatSeconds(sectionRemaining)} left in this part`
      : itemRemaining === 10
        ? "Ten seconds left for this question"
        : "";

  return (
    <header className={styles.header}>
      <div className={styles.headerInner}>
        <div>
          <div className={styles.partName}>{partTitle}</div>
          {taskName && <div className={styles.taskName}>{taskName}</div>}
        </div>
        <span className={styles.counter}>
          Question {position} of {total}
        </span>
        <div className={styles.clocks}>
          {sectionRemaining !== null && (
            <div className={styles.clock}>
              <div className={styles.clockLabel}>Part time left</div>
              <div className={clockClass(sectionRemaining, "part")}>{formatSeconds(sectionRemaining)}</div>
            </div>
          )}
          {itemRemaining !== null && (
            <div className={styles.clock}>
              <div className={styles.clockLabel}>Time to answer</div>
              <div className={clockClass(itemRemaining, "item")}>{formatSeconds(itemRemaining)}</div>
            </div>
          )}
        </div>
      </div>
      <div aria-live="assertive" className="visually-hidden">
        {announce}
      </div>
    </header>
  );
}
