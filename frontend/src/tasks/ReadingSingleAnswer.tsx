import { ChoiceList } from "./shared/ChoiceList";
import styles from "./Tasks.module.css";
import type { TaskProps } from "./types";

export default function ReadingSingleAnswer({ question, response, onChange, locked, review }: TaskProps) {
  const { passage, question: prompt, options = [] } = question.display;
  return (
    <>
      <div className={styles.panel}>
        <p className={styles.passage}>{passage}</p>
      </div>
      <div className={styles.panel}>
        <p className={styles.questionText}>{prompt}</p>
        <ChoiceList
          name="mcsa"
          options={options}
          multiple={false}
          selected={response.selected}
          onChange={(selected) => onChange({ selected })}
          locked={locked}
          correct={review ? question.answer?.correct : undefined}
        />
      </div>
    </>
  );
}
