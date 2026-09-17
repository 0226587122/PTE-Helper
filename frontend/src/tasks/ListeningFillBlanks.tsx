import { AudioPanel } from "./shared/AudioPanel";
import { Blanks } from "./shared/Blanks";
import styles from "./Tasks.module.css";
import type { TaskProps } from "./types";

export default function ListeningFillBlanks({ question, response, onChange, locked, review, stage, speaking }: TaskProps) {
  return (
    <>
      <AudioPanel stage={stage} speaking={speaking} />
      <div className={styles.panel}>
        <Blanks
          mode="type"
          segments={question.display.segments ?? []}
          answers={response.answers ?? []}
          onChange={(answers) => onChange({ answers })}
          locked={locked}
          correct={review ? question.answer?.blanks : undefined}
        />
      </div>
    </>
  );
}
