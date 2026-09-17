import { AudioPanel } from "./shared/AudioPanel";
import styles from "./Tasks.module.css";
import type { TaskProps } from "./types";

export default function HighlightIncorrectWords({ question, response, onChange, locked, review, stage, speaking }: TaskProps) {
  const tokens = question.display.tokens ?? [];
  const selected = new Set(Array.isArray(response.selected) ? response.selected : []);
  const incorrect = new Set(review ? question.answer?.incorrect ?? [] : []);
  const originals = question.answer?.originals ?? {};

  const toggle = (index: number) => {
    const next = new Set(selected);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    onChange({ selected: [...next].sort((a, b) => a - b) });
  };

  return (
    <>
      <AudioPanel stage={stage} speaking={speaking} />
      <div className={styles.panel}>
        <p className={styles.tokens}>
          {tokens.map((token, index) => {
            let className = selected.has(index) ? styles.tokenSelected : styles.token;
            if (review) {
              if (incorrect.has(index) && selected.has(index)) className = styles.tokenCorrect;
              else if (incorrect.has(index)) className = styles.tokenMissed;
              else if (selected.has(index)) className = styles.tokenWrong;
            }
            return (
              <span key={index}>
                <button
                  type="button"
                  className={className}
                  onClick={() => toggle(index)}
                  disabled={locked}
                  aria-pressed={selected.has(index)}
                >
                  {token}
                </button>
                {review && incorrect.has(index) && <span className={styles.original}>({originals[String(index)]})</span>}{" "}
              </span>
            );
          })}
        </p>
        {review && (
          <p className={styles.audioHint}>
            Green words were changed and you found them. Words underlined in green were changed but missed. Crossed-out words
            were clicked but were correct. The word the speaker actually said is shown in brackets.
          </p>
        )}
      </div>
    </>
  );
}
