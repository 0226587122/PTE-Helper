import { useState, type DragEvent } from "react";

import styles from "./Tasks.module.css";
import type { TaskProps } from "./types";

/**
 * Move paragraphs from the source column into the target column and put them in order.
 * Works with drag and drop, and with the buttons for keyboard and touch users.
 */
export default function ReorderParagraphs({ question, response, onChange, locked, review }: TaskProps) {
  const paragraphs = question.display.paragraphs ?? [];
  const order = response.order ?? [];
  const byId = Object.fromEntries(paragraphs.map((p) => [p.id, p.text]));
  const source = paragraphs.filter((p) => !order.includes(p.id));
  const [dragging, setDragging] = useState<string | null>(null);
  const correctOrder = review ? question.answer?.order ?? [] : [];

  const setOrder = (next: string[]) => onChange({ order: next });
  const add = (id: string, index = order.length) => {
    const next = order.filter((x) => x !== id);
    next.splice(index, 0, id);
    setOrder(next);
  };
  const remove = (id: string) => setOrder(order.filter((x) => x !== id));
  const move = (index: number, delta: number) => {
    const next = [...order];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setOrder(next);
  };

  const dropOnTarget = (index?: number) => (event: DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    if (dragging && !locked) add(dragging, index);
    setDragging(null);
  };

  const pairIsCorrect = (i: number) => {
    const a = correctOrder.indexOf(order[i]);
    return a !== -1 && correctOrder[a + 1] === order[i + 1];
  };

  return (
    <div className={styles.reorder}>
      <section
        className={styles.reorderColumn}
        aria-label="Source"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (dragging && !locked) remove(dragging);
          setDragging(null);
        }}
      >
        <h3>Source</h3>
        {source.map((p) => (
          <div
            key={p.id}
            className={styles.paragraph}
            draggable={!locked}
            onDragStart={() => setDragging(p.id)}
            data-testid={`source-${p.id}`}
          >
            <span className={styles.paragraphLabel}>{p.id}</span>
            <span className={styles.paragraphText}>{p.text}</span>
            <div className={styles.paragraphActions}>
              <button type="button" className={styles.iconButton} onClick={() => add(p.id)} disabled={locked} aria-label={`Move paragraph ${p.id} to your answer`}>
                →
              </button>
            </div>
          </div>
        ))}
        {source.length === 0 && <p className={styles.audioHint}>All paragraphs placed.</p>}
      </section>

      <section className={styles.reorderColumn} aria-label="Target" onDragOver={(e) => e.preventDefault()} onDrop={dropOnTarget()}>
        <h3>Your order</h3>
        {order.map((id, i) => (
          <div
            key={id}
            className={styles.paragraph}
            draggable={!locked}
            onDragStart={() => setDragging(id)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={dropOnTarget(i)}
            data-testid={`target-${id}`}
          >
            <span className={styles.paragraphLabel}>{i + 1}</span>
            <span className={styles.paragraphText}>
              {byId[id]}
              {review && i < order.length - 1 && (
                <div className={pairIsCorrect(i) ? styles.wordCountIn : styles.wordCountOut}>
                  {pairIsCorrect(i) ? "✓ Correct link to the next paragraph" : "✗ The next paragraph doesn't follow this one"}
                </div>
              )}
            </span>
            <div className={styles.paragraphActions}>
              <button type="button" className={styles.iconButton} onClick={() => move(i, -1)} disabled={locked || i === 0} aria-label={`Move paragraph ${id} up`}>
                ↑
              </button>
              <button
                type="button"
                className={styles.iconButton}
                onClick={() => move(i, 1)}
                disabled={locked || i === order.length - 1}
                aria-label={`Move paragraph ${id} down`}
              >
                ↓
              </button>
              <button type="button" className={styles.iconButton} onClick={() => remove(id)} disabled={locked} aria-label={`Move paragraph ${id} back`}>
                ←
              </button>
            </div>
          </div>
        ))}
        {order.length === 0 && <p className={styles.audioHint}>Drag paragraphs here, or use the → buttons.</p>}
      </section>

      {review && (
        <section className={styles.correctAnswer} style={{ gridColumn: "1 / -1" }}>
          <strong>Correct order:</strong>
          <ol className={styles.keyPoints}>
            {correctOrder.map((id) => (
              <li key={id}>{byId[id]}</li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
