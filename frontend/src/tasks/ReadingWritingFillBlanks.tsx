import { Blanks } from "./shared/Blanks";
import styles from "./Tasks.module.css";
import type { TaskProps } from "./types";

export default function ReadingWritingFillBlanks({ question, response, onChange, locked, review }: TaskProps) {
  return (
    <div className={styles.panel}>
      <Blanks
        mode="dropdown"
        segments={question.display.segments ?? []}
        answers={response.answers ?? []}
        onChange={(answers) => onChange({ answers })}
        locked={locked}
        correct={review ? question.answer?.blanks : undefined}
      />
    </div>
  );
}
