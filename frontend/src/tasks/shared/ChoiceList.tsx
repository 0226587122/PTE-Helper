import styles from "../Tasks.module.css";

interface Props {
  name: string;
  options: string[];
  multiple: boolean;
  selected: number | number[] | undefined;
  onChange: (selected: number | number[]) => void;
  locked: boolean;
  /** Correct option index (or indexes) once the question has been marked. */
  correct?: number | number[];
}

/** Radio buttons for single-answer tasks and checkboxes for multiple-answer tasks. */
export function ChoiceList({ name, options, multiple, selected, onChange, locked, correct }: Props) {
  const chosen = new Set(Array.isArray(selected) ? selected : selected === undefined ? [] : [selected]);
  const right = new Set(Array.isArray(correct) ? correct : correct === undefined ? [] : [correct]);
  const reviewing = correct !== undefined;

  const toggle = (index: number) => {
    if (multiple) {
      const next = new Set(chosen);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      onChange([...next].sort((a, b) => a - b));
    } else {
      onChange(index);
    }
  };

  return (
    <ul className={styles.choices} role={multiple ? "group" : "radiogroup"}>
      {options.map((option, index) => {
        const isChosen = chosen.has(index);
        const isRight = right.has(index);
        let className = styles.choice;
        let mark = "";
        if (reviewing && isRight) {
          className = `${styles.choice} ${styles.choiceCorrect}`;
          mark = isChosen ? "✓ Correct" : "Correct answer";
        } else if (reviewing && isChosen) {
          className = `${styles.choice} ${styles.choiceWrong}`;
          mark = "✗ Incorrect";
        } else if (isChosen) {
          className = `${styles.choice} ${styles.choiceSelected}`;
        }
        return (
          <li key={index}>
            <label className={className}>
              <input
                type={multiple ? "checkbox" : "radio"}
                name={name}
                checked={isChosen}
                onChange={() => toggle(index)}
                disabled={locked}
              />
              <span>{option}</span>
              {mark && <span className={styles.mark}>{mark}</span>}
            </label>
          </li>
        );
      })}
    </ul>
  );
}
