import { KeyPoints } from "./shared/ReviewNotes";
import { WritingBox } from "./shared/WritingBox";
import styles from "./Tasks.module.css";
import type { TaskProps } from "./types";

export default function SummarizeWrittenText({ question, response, onChange, locked, review }: TaskProps) {
  return (
    <>
      <div className={styles.panel}>
        <p className={styles.passage}>{question.display.passage}</p>
      </div>
      <WritingBox
        label="Your one-sentence summary"
        value={response.text ?? ""}
        onChange={(text) => onChange({ text })}
        locked={locked}
        review={review}
        min={5}
        max={75}
        short
        placeholder="Write one sentence that summarises the passage."
      />
      {review && <KeyPoints points={question.answer?.key_points} />}
    </>
  );
}
