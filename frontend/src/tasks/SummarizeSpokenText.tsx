import { AudioPanel } from "./shared/AudioPanel";
import { KeyPoints, Transcript } from "./shared/ReviewNotes";
import { WritingBox } from "./shared/WritingBox";
import type { TaskProps } from "./types";

export default function SummarizeSpokenText({ question, response, onChange, locked, review, stage, speaking }: TaskProps) {
  return (
    <>
      <AudioPanel stage={stage} speaking={speaking} label="Lecture" />
      <WritingBox
        label="Your summary"
        value={response.text ?? ""}
        onChange={(text) => onChange({ text })}
        locked={locked}
        review={review}
        min={50}
        max={70}
        placeholder="Take notes while you listen, then write a 50 to 70 word summary."
      />
      {review && (
        <>
          <KeyPoints points={question.answer?.key_points} />
          <Transcript transcript={question.answer?.transcript} />
        </>
      )}
    </>
  );
}
