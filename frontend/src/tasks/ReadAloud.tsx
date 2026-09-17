import { SpokenAnswer } from "./shared/SpokenAnswer";
import styles from "./Tasks.module.css";
import type { TaskProps } from "./types";

export default function ReadAloud(props: TaskProps) {
  return (
    <>
      <div className={styles.panel}>
        <p className={styles.readText}>{props.question.display.text}</p>
      </div>
      <SpokenAnswer {...props} />
    </>
  );
}
