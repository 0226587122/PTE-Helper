import { KeyPoints } from "./shared/ReviewNotes";
import { WritingBox } from "./shared/WritingBox";
import styles from "./Tasks.module.css";
import type { TaskProps } from "./types";

export default function WriteEssay({ question, response, onChange, locked, review }: TaskProps) {
  return (
    <>
      <div className={styles.panel}>
        <p className={styles.readText}>{question.display.prompt}</p>
      </div>
      <WritingBox
        label="Your essay"
        value={response.text ?? ""}
        onChange={(text) => onChange({ text })}
        locked={locked}
        review={review}
        min={200}
        max={300}
        placeholder="Plan, write and check your essay. Separate paragraphs with a blank line."
      />
      {review && <KeyPoints points={question.answer?.key_points} title="Ideas you could discuss" />}
    </>
  );
}
