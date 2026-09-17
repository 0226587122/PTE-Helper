import { AudioPanel } from "./shared/AudioPanel";
import { KeyPoints, Transcript } from "./shared/ReviewNotes";
import { SpokenAnswer } from "./shared/SpokenAnswer";
import type { TaskProps } from "./types";

export default function RetellLecture(props: TaskProps) {
  const { stage, speaking, review, question } = props;
  return (
    <>
      <AudioPanel stage={stage} speaking={speaking} label="Lecture" />
      <SpokenAnswer {...props} />
      {review && (
        <>
          <KeyPoints points={question.answer?.key_points} />
          <Transcript transcript={question.answer?.transcript} />
        </>
      )}
    </>
  );
}
