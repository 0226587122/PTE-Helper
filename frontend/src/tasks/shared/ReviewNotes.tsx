import type { ReactNode } from "react";

import type { Turn } from "../../api/types";
import styles from "../Tasks.module.css";

export function KeyPoints({ points, title = "A strong answer covers" }: { points?: string[]; title?: string }) {
  if (!points?.length) return null;
  return (
    <div className={styles.correctAnswer}>
      <strong>{title}:</strong>
      <ul className={styles.keyPoints}>
        {points.map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ul>
    </div>
  );
}

export function CorrectAnswer({ label = "Correct answer", children }: { label?: string; children: ReactNode }) {
  return (
    <div className={styles.correctAnswer}>
      <strong>{label}:</strong> {children}
    </div>
  );
}

export function Transcript({ transcript }: { transcript?: string | Turn[] }) {
  if (!transcript) return null;
  return (
    <details className={styles.panel}>
      <summary>Show the audio transcript</summary>
      {typeof transcript === "string" ? (
        <p className={styles.passage}>{transcript}</p>
      ) : (
        <div className={styles.speakers}>
          {transcript.map((t, i) => (
            <div key={i} className={styles.speakerLine}>
              <strong>{t.speaker}:</strong> {t.text}
            </div>
          ))}
        </div>
      )}
    </details>
  );
}
