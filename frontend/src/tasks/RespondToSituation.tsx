import { AudioPanel } from "./shared/AudioPanel";
import { KeyPoints } from "./shared/ReviewNotes";
import { SpokenAnswer } from "./shared/SpokenAnswer";
import styles from "./Tasks.module.css";
import type { TaskProps } from "./types";

export default function RespondToSituation(props: TaskProps) {
  const { stage, speaking, review, question } = props;
  return (
    <>
      <div className={styles.panel}>
        <p className={styles.readText}>{question.display.situation}</p>
      </div>
      <AudioPanel stage={stage} speaking={speaking} label="Situation" />
      <SpokenAnswer {...props} />
      {review && <KeyPoints points={question.answer?.key_points} />}
    </>
  );
}
