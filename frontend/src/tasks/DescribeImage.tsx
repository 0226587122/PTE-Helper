import { Chart } from "./shared/Chart";
import { CorrectAnswer, KeyPoints } from "./shared/ReviewNotes";
import { SpokenAnswer } from "./shared/SpokenAnswer";
import styles from "./Tasks.module.css";
import type { TaskProps } from "./types";

export default function DescribeImage(props: TaskProps) {
  const { question, review } = props;
  return (
    <>
      <div className={styles.panel}>{question.display.chart && <Chart data={question.display.chart} />}</div>
      <SpokenAnswer {...props} />
      {review && (
        <>
          <KeyPoints points={question.answer?.key_points} title="Try to mention" />
          {question.answer?.notes && <CorrectAnswer label="Key figures">{question.answer.notes}</CorrectAnswer>}
        </>
      )}
    </>
  );
}
