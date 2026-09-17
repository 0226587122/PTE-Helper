import { AudioPanel } from "./shared/AudioPanel";
import { CorrectAnswer } from "./shared/ReviewNotes";
import { SpokenAnswer } from "./shared/SpokenAnswer";
import type { TaskProps } from "./types";

export default function RepeatSentence(props: TaskProps) {
  const { stage, speaking, review, question } = props;
  return (
    <>
      <AudioPanel stage={stage} speaking={speaking} />
      <SpokenAnswer {...props} />
      {review && <CorrectAnswer label="The sentence was">{question.answer?.sentence}</CorrectAnswer>}
    </>
  );
}
