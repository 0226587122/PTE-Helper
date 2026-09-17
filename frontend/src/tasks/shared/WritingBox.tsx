import styles from "../Tasks.module.css";

export function countWords(text: string): number {
  return (text.match(/[A-Za-z0-9]+(?:['’][A-Za-z]+)?/g) ?? []).length;
}

interface Props {
  value: string;
  onChange: (value: string) => void;
  locked: boolean;
  review: boolean;
  min?: number;
  max?: number;
  short?: boolean;
  label: string;
  placeholder?: string;
}

/** A text box with a live word counter. It locks when time runs out. */
export function WritingBox({ value, onChange, locked, review, min, max, short, label, placeholder }: Props) {
  const words = countWords(value);
  const inRange = (min === undefined || words >= min) && (max === undefined || words <= max);
  return (
    <div>
      <label className="visually-hidden" htmlFor="answer-box">
        {label}
      </label>
      <textarea
        id="answer-box"
        className={short ? styles.textareaShort : styles.textarea}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={locked}
        placeholder={placeholder}
        spellCheck={false}
        autoCorrect="off"
        autoCapitalize="off"
      />
      <div className={styles.wordCount}>
        <span>
          {locked && !review ? <span className={styles.lockedNote}>Time's up. Your answer is locked.</span> : null}
        </span>
        <span className={min !== undefined || max !== undefined ? (inRange ? styles.wordCountIn : styles.wordCountOut) : undefined}>
          Word count: {words}
          {min !== undefined && max !== undefined ? ` (aim for ${min} to ${max})` : ""}
        </span>
      </div>
    </div>
  );
}
