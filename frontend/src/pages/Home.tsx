import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useProgress, useStartSet, useTaskTypes } from "../api/hooks";
import type { Section, TaskType, TypeProgress } from "../api/types";
import { ErrorMessage, Loading } from "../components/Loading";
import { formatSeconds } from "../hooks/useExamTimer";
import styles from "./Pages.module.css";

const SECTIONS: { id: Section; title: string; colour: string }[] = [
  { id: "speaking_writing", title: "Speaking & Writing", colour: "var(--speaking)" },
  { id: "reading", title: "Reading", colour: "var(--reading)" },
  { id: "listening", title: "Listening", colour: "var(--listening)" },
];

export const BANDS = [
  { min: 10, max: 29, label: "Getting started" },
  { min: 30, max: 49, label: "Building skills" },
  { min: 50, max: 64, label: "Competent" },
  { min: 65, max: 78, label: "Strong" },
  { min: 79, max: 90, label: "Expert" },
];

export function bandFor(score: number) {
  return BANDS.find((b) => score >= b.min && score <= b.max) ?? BANDS[0];
}

function ReadinessScale({ estimate }: { estimate: number | null }) {
  const position = estimate === null ? null : ((estimate - 10) / 80) * 100;
  const band = estimate === null ? null : bandFor(estimate);
  return (
    <div className={styles.scale}>
      <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem" }}>
        <span className={styles.estimate}>{estimate ?? "–"}</span>
        <span>
          {estimate === null
            ? "Finish a practice set to see your readiness estimate."
            : `${band!.label} · practice estimate on the 10 to 90 scale`}
        </span>
      </div>
      <div className={styles.scaleTrack} aria-hidden style={{ marginTop: "0.9rem" }}>
        {position !== null && <div className={styles.scaleMarker} style={{ left: `${position}%` }} />}
      </div>
      <div className={styles.scaleLabels} aria-hidden>
        {[10, 30, 50, 65, 79, 90].map((value) => (
          <span key={value} style={{ left: `${((value - 10) / 80) * 100}%` }}>
            {value}
          </span>
        ))}
      </div>
      <div className={styles.scaleBands}>
        {BANDS.map((b) => (
          <span
            key={b.label}
            style={{ flexBasis: `${((Math.min(b.max + 1, 90) - b.min) / 80) * 100}%` }}
            className={band?.label === b.label ? styles.bandActive : undefined}
          >
            {b.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function timingText(type: TaskType) {
  const parts: string[] = [];
  if (type.prep_seconds) parts.push(`${type.prep_seconds}s prep`);
  parts.push(`${formatSeconds(type.answer_seconds)} ${type.spoken ? "to speak" : "to answer"}`);
  return parts.join(" · ");
}

function TaskCard({ type, progress }: { type: TaskType; progress?: TypeProgress }) {
  const start = useStartSet();
  const navigate = useNavigate();
  return (
    <article className={styles.card}>
      <div className={styles.cardTop}>
        <span className={styles.cardName}>{type.name}</span>
        <span className={styles.code}>{type.code}</span>
      </div>
      <div className={styles.meta}>{timingText(type)}</div>
      <div className={styles.badges}>
        {type.audio && <span className={styles.badge}>Audio</span>}
        {type.spoken && <span className={styles.badge}>Microphone</span>}
        {type.ai_feedback && <span className={styles.badgeAi}>Examiner feedback</span>}
      </div>
      <div className={styles.scores}>
        {progress ? (
          <>
            Best <strong>{progress.best_score}</strong> · Last <strong>{progress.last_score}</strong> ·{" "}
            {progress.sets_completed} set{progress.sets_completed === 1 ? "" : "s"}
          </>
        ) : (
          <span className={styles.meta}>Not practised yet</span>
        )}
      </div>
      {start.error && <span className={styles.meta} style={{ color: "var(--red)" }}>{(start.error as ApiError).message}</span>}
      <button
        type="button"
        className={styles.startButton}
        disabled={start.isPending}
        onClick={() => start.mutate(type.code, { onSuccess: (set) => navigate(`/practice/${set.id}`) })}
        aria-label={`Start 15 ${type.name} questions`}
      >
        {start.isPending ? "Preparing questions…" : "Start practice set"}
      </button>
    </article>
  );
}

export default function Home() {
  const types = useTaskTypes();
  const progress = useProgress();

  if (types.isLoading) return <Loading />;
  if (types.error) return <ErrorMessage error={types.error} />;
  const byCode = Object.fromEntries((progress.data?.types ?? []).map((t) => [t.code, t]));

  return (
    <>
      <section className={styles.hero}>
        <h1>Your PTE Academic readiness</h1>
        <p className={styles.heroText}>
          Each practice set has 15 random questions with real exam timing. Scores are practice estimates to guide your
          study, not official Pearson results.
        </p>
        <ReadinessScale estimate={progress.data?.overall_estimate ?? null} />
      </section>

      {SECTIONS.map((section) => (
        <section key={section.id} className={styles.section}>
          <h2 className={styles.sectionTitle}>
            <span className={styles.sectionDot} style={{ background: section.colour }} aria-hidden />
            {section.title}
          </h2>
          <div className={styles.grid}>
            {(types.data ?? [])
              .filter((t) => t.section === section.id)
              .map((t) => (
                <TaskCard key={t.code} type={t} progress={byCode[t.code]} />
              ))}
          </div>
        </section>
      ))}

      {progress.data && progress.data.recent.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Recent practice</h2>
          <div style={{ overflowX: "auto" }}>
            <table className={styles.history}>
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Finished</th>
                  <th>Average</th>
                  <th>Practice estimate</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {progress.data.recent.map((r) => (
                  <tr key={r.set_id}>
                    <td>{r.name}</td>
                    <td>{new Date(r.finished_at + "Z").toLocaleDateString()}</td>
                    <td>{Math.round(r.average_pct)}%</td>
                    <td>{r.estimated_score}</td>
                    <td>
                      <Link to={`/results/${r.set_id}`}>Review</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}
