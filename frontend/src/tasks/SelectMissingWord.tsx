import { AudioPanel } from "./shared/AudioPanel";
import { ChoiceList } from "./shared/ChoiceList";
import { Transcript } from "./shared/ReviewNotes";
import styles from "./Tasks.module.css";
import type { TaskProps } from "./types";

export default function SelectMissingWord({ question, response, onChange, locked, review, stage, speaking }: TaskProps) {
  return (
    <>
      <AudioPanel stage={stage} speaking={speaking} />
      <div className={styles.panel}>
        <p className={styles.questionText}>Which words complete the recording?</p>
        <ChoiceList
          name="smw"
          options={question.display.options ?? []}
          multiple={false}
          selected={response.selected}
          onChange={(selected) => onChange({ selected })}
          locked={locked}
          correct={review ? question.answer?.correct : undefined}
        />
      </div>
      {review && <Transcript transcript={question.answer?.transcript} />}
    </>
  );
}
