import type { BlueprintPart } from "../api/types";
import styles from "./Mock.module.css";

/** The instruction screen shown at the start of each part, as in the real test. */
export function PartIntro({ part, onStart }: { part: BlueprintPart; onStart: () => void }) {
  const minutes =
    part.minutes.min === part.minutes.max ? `${part.minutes.min} minutes` : `${part.minutes.min} to ${part.minutes.max} minutes`;
  return (
    <div className={styles.card}>
      <h1>{part.title}</h1>
      <p>
        <strong>About {minutes}.</strong> {part.instructions}
      </p>
      <p className={styles.types}>
        This part contains: {part.task_types.map((t) => t.name).join(", ")}.
      </p>
      {part.allow_back ? (
        <p className={styles.saveNote}>The clock starts when you open the first question and runs for the whole part.</p>
      ) : (
        <p className={styles.saveNote}>Each question starts its own clock as soon as it appears.</p>
      )}
      <button type="button" className={styles.primary} onClick={onStart} autoFocus>
        Start {part.title.split(":")[0].toLowerCase()}
      </button>
    </div>
  );
}
