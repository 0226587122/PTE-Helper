import { AudioPanel } from "./shared/AudioPanel";
import { KeyPoints, Transcript } from "./shared/ReviewNotes";
import { SpokenAnswer } from "./shared/SpokenAnswer";
import type { TaskProps } from "./types";

export default function SummarizeGroupDiscussion(props: TaskProps) {
  const { stage, speaking, review, question } = props;
  const speakers = [...new Set((question.display.turns ?? []).map((t) => t.speaker))];
  return (
    <>
      <AudioPanel stage={stage} speaking={speaking} label={`Discussion with ${speakers.join(", ")}`} />
      <SpokenAnswer {...props} />
      {review && (
        <>
          <KeyPoints points={question.answer?.key_points} />
          <Transcript transcript={question.display.turns} />
        </>
      )}
    </>
  );
}
