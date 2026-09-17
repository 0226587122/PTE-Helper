import { Blanks } from "./shared/Blanks";
import styles from "./Tasks.module.css";
import type { TaskProps } from "./types";

export default function ReadingFillBlanks({ question, response, onChange, locked, review }: TaskProps) {
  return (
    <div className={styles.panel}>
      <Blanks
        mode="drag"
        segments={question.display.segments ?? []}
        bank={question.display.bank ?? []}
        answers={response.answers ?? []}
        onChange={(answers) => onChange({ answers })}
        locked={locked}
        correct={review ? question.answer?.blanks : undefined}
      />
    </div>
  );
}
