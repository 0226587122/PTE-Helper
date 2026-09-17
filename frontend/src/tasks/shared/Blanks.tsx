import { useState, type DragEvent } from "react";

import type { BlankSegment } from "../../api/types";
import styles from "../Tasks.module.css";

type Mode = "dropdown" | "drag" | "type";

interface Props {
  mode: Mode;
  segments: BlankSegment[];
  bank?: string[];
  answers: (string | null)[];
  onChange: (answers: (string | null)[]) => void;
  locked: boolean;
  correct?: string[];
}

const same = (a: string | null | undefined, b: string) => (a ?? "").trim().toLowerCase() === b.trim().toLowerCase();

/**
 * Passages with blanks, in three styles:
 * dropdown (Reading & Writing FIB), drag from a word bank (Reading FIB) and typed answers (Listening FIB).
 * Drag and drop also works by clicking a word and then clicking a blank, for keyboard and touch users.
 */
export function Blanks({ mode, segments, bank = [], answers, onChange, locked, correct }: Props) {
  const [picked, setPicked] = useState<string | null>(null);
  const [hover, setHover] = useState<number | null>(null);
  const blankCount = segments.filter((s) => typeof s !== "string").length;
  const values = Array.from({ length: blankCount }, (_, i) => answers[i] ?? null);

  const setBlank = (index: number, value: string | null) => {
    const next = [...values];
    // A word from the bank can only sit in one blank at a time.
    if (mode === "drag" && value !== null) {
      const existing = next.indexOf(value);
      if (existing !== -1) next[existing] = null;
    }
    next[index] = value;
    onChange(next);
  };

  const reviewClass = (index: number) => {
    if (!correct) return "";
    return same(values[index], correct[index]) ? styles.blankCorrect : styles.blankWrong;
  };

  const used = new Set(values.filter(Boolean));
  const available = bank.filter((word) => !used.has(word));

  const onDrop = (index: number) => (event: DragEvent) => {
    event.preventDefault();
    setHover(null);
    const word = event.dataTransfer.getData("text/plain");
    if (word && !locked) setBlank(index, word);
  };

  return (
    <div>
      <p className={styles.passage}>
        {segments.map((segment, i) => {
          if (typeof segment === "string") return <span key={i}>{segment}</span>;
          const index = segment.blank;
          const hint =
            correct && !same(values[index], correct[index]) ? (
              <span className={styles.answerHint}>({correct[index]})</span>
            ) : null;

          if (mode === "dropdown") {
            return (
              <span key={i}>
                <select
                  aria-label={`Blank ${index + 1}`}
                  className={`${styles.blankSelect} ${reviewClass(index)}`}
                  value={values[index] ?? ""}
                  onChange={(e) => setBlank(index, e.target.value || null)}
                  disabled={locked}
                >
                  <option value="">Select…</option>
                  {(segment.options ?? []).map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
                {hint}
              </span>
            );
          }

          if (mode === "type") {
            return (
              <span key={i}>
                <input
                  aria-label={`Blank ${index + 1}`}
                  className={`${styles.blankInput} ${reviewClass(index)}`}
                  value={values[index] ?? ""}
                  onChange={(e) => setBlank(index, e.target.value)}
                  disabled={locked}
                  autoComplete="off"
                  autoCorrect="off"
                  autoCapitalize="off"
                  spellCheck={false}
                />
                {hint}
              </span>
            );
          }

          return (
            <span key={i}>
              <button
                type="button"
                aria-label={`Blank ${index + 1}${values[index] ? `: ${values[index]}` : ""}`}
                className={`${styles.blankDrop} ${hover === index ? styles.blankDropTarget : ""} ${reviewClass(index)}`}
                disabled={locked}
                onClick={() => {
                  if (picked) {
                    setBlank(index, picked);
                    setPicked(null);
                  } else if (values[index]) {
                    setBlank(index, null);
                  }
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  setHover(index);
                }}
                onDragLeave={() => setHover(null)}
                onDrop={onDrop(index)}
              >
                {values[index] ?? " "}
              </button>
              {hint}
            </span>
          );
        })}
      </p>

      {mode === "drag" && (
        <div className={styles.bank} aria-label="Word bank">
          {available.map((word) => (
            <button
              key={word}
              type="button"
              draggable={!locked}
              className={picked === word ? styles.chipSelected : styles.chip}
              onDragStart={(e) => e.dataTransfer.setData("text/plain", word)}
              onClick={() => setPicked(picked === word ? null : word)}
              disabled={locked}
              aria-pressed={picked === word}
            >
              {word}
            </button>
          ))}
          {available.length === 0 && <span className={styles.audioHint}>All words placed.</span>}
        </div>
      )}
    </div>
  );
}
