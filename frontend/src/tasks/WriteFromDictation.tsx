import { AudioPanel } from "./shared/AudioPanel";
import { CorrectAnswer } from "./shared/ReviewNotes";
import styles from "./Tasks.module.css";
import type { TaskProps } from "./types";

export default function WriteFromDictation({ question, response, onChange, locked, review, stage, speaking }: TaskProps) {
  return (
    <>
      <AudioPanel stage={stage} speaking={speaking} />
      <div className={styles.panel}>
        <label htmlFor="dictation" className={styles.questionText} style={{ display: "block" }}>
          Type the sentence you hear
        </label>
        <textarea
          id="dictation"
          className={styles.textareaShort}
          value={response.text ?? ""}
          onChange={(e) => onChange({ text: e.target.value })}
          disabled={locked}
          spellCheck={false}
          autoCorrect="off"
          autoCapitalize="off"
        />
        {review && <CorrectAnswer label="The sentence was">{question.answer?.sentence}</CorrectAnswer>}
      </div>
    </>
  );
}
