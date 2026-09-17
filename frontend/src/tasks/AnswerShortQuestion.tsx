import { AudioPanel } from "./shared/AudioPanel";
import { CorrectAnswer, Transcript } from "./shared/ReviewNotes";
import { SpokenAnswer } from "./shared/SpokenAnswer";
import type { TaskProps } from "./types";

export default function AnswerShortQuestion(props: TaskProps) {
  const { stage, speaking, review, question } = props;
  return (
    <>
      <AudioPanel stage={stage} speaking={speaking} label="Question" />
      <SpokenAnswer {...props} />
      {review && (
        <>
          <CorrectAnswer label="Accepted answers">{question.answer?.accepted?.join(", ")}</CorrectAnswer>
          <Transcript transcript={question.answer?.transcript} />
        </>
      )}
    </>
  );
}
