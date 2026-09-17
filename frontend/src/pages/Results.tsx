import { Link, useParams } from "react-router-dom";

import { useFinishSet, useReview, useSet, useTaskTypes } from "../api/hooks";
import { ErrorMessage, Loading } from "../components/Loading";
import { ResultPanel } from "../components/ResultPanel";
import { TASKS } from "../tasks";
import { bandFor } from "./Home";
import styles from "./Pages.module.css";

export default function Results() {
  const setId = Number(useParams().setId);
  const set = useSet(setId);
  const review = useReview(setId);
  const types = useTaskTypes();
  const finish = useFinishSet(setId);

  if (set.isLoading || types.isLoading || review.isLoading) return <Loading />;
  if (set.error) return <ErrorMessage error={set.error} />;
  const type = types.data?.find((t) => t.code === set.data?.task_type);
  if (!set.data || !type) return <ErrorMessage error={new Error("We couldn't load these results.")} />;
  const Task = TASKS[type.code];

  if (!set.data.finished_at) {
    return (
      <div className={styles.authCard}>
        <h1>This set isn't finished yet</h1>
        <p>
          You've answered {set.data.answered_count} of {set.data.question_count} questions.
        </p>
        <div style={{ display: "flex", gap: "1rem" }}>
          <Link to={`/practice/${setId}`}>Keep practising</Link>
          <button type="button" className={styles.linkish} onClick={() => finish.mutate()}>
            Finish and see results
          </button>
        </div>
      </div>
    );
  }

  const estimate = set.data.estimated_score ?? 10;
  return (
    <div>
      <section className={styles.resultsHero}>
        <div>
          <div className={styles.heroText}>Practice estimate</div>
          <div className={styles.estimate} style={{ fontSize: "3rem" }}>
            {estimate}
            <span style={{ fontSize: "1.2rem", fontWeight: 600 }}> / 90</span>
          </div>
          <div>{bandFor(estimate).label}</div>
        </div>
        <div>
          <h1>{type.name}</h1>
          <p className={styles.heroText}>
            You answered {set.data.answered_count} of {set.data.question_count} questions with an average of{" "}
            {Math.round(set.data.average_pct ?? 0)}%. This is a practice estimate, not an official Pearson score.
          </p>
          <p className={styles.heroText} style={{ margin: 0 }}>
            <strong>Tip:</strong> {type.tip}
          </p>
        </div>
      </section>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
        <Link to="/">Back to all tasks</Link>
      </div>

      <h2>Review your answers</h2>
      {review.error && <ErrorMessage error={review.error} />}
      {review.data?.map((q) => (
        <details key={q.position} className={styles.reviewItem}>
          <summary>
            <span>Question {q.position}</span>
            <span>{q.answered ? `${Math.round(q.result?.pct ?? 0)}%` : "Not answered"}</span>
          </summary>
          <div className={styles.reviewBody}>
            {q.answered ? (
              <>
                <Task
                  type={type}
                  question={q}
                  response={q.response ?? {}}
                  onChange={() => {}}
                  locked
                  review
                  stage="done"
                  speaking={false}
                />
                <ResultPanel question={q} type={type} showTip={false} />
              </>
            ) : (
              <p className={styles.meta}>You didn't answer this question, so it counts as zero.</p>
            )}
          </div>
        </details>
      ))}
    </div>
  );
}
