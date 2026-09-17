import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { useFinishSet, useQuestion, useSet, useTaskTypes } from "../api/hooks";
import { ErrorMessage, Loading } from "../components/Loading";
import { QuestionRunner } from "../components/QuestionRunner";
import styles from "./Pages.module.css";

export default function Practice() {
  const setId = Number(useParams().setId);
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const set = useSet(setId);
  const types = useTaskTypes();
  const finish = useFinishSet(setId);
  const [showTip, setShowTip] = useState(false);

  const position = Number(params.get("q")) || 0;
  const question = useQuestion(setId, position);

  useEffect(() => {
    if (set.data?.finished_at) navigate(`/results/${setId}`, { replace: true });
  }, [set.data?.finished_at, navigate, setId]);

  // Pin the current question in the URL so answering doesn't move on until the student chooses to.
  useEffect(() => {
    if (!set.data || position) return;
    const firstUnanswered = set.data.questions.find((q) => !q.answered)?.position ?? set.data.question_count;
    setParams({ q: String(firstUnanswered) }, { replace: true });
  }, [set.data, position, setParams]);

  if (set.isLoading || types.isLoading || !position) return <Loading />;
  if (set.error) return <ErrorMessage error={set.error} />;
  const type = types.data?.find((t) => t.code === set.data!.task_type);
  if (!set.data || !type) return <ErrorMessage error={new Error("We couldn't load this practice set.")} />;

  const total = set.data.question_count;
  const isLast = position >= total;
  const answeredPositions = new Set(set.data.questions.filter((q) => q.answered).map((q) => q.position));

  const goNext = () => {
    if (isLast) {
      finish.mutate(undefined, { onSuccess: () => navigate(`/results/${setId}`) });
    } else {
      setParams({ q: String(position + 1) });
      window.scrollTo({ top: 0 });
    }
  };

  const finishEarly = () => {
    if (window.confirm("Finish this set now? Questions you haven't answered will count as zero.")) {
      finish.mutate(undefined, { onSuccess: () => navigate(`/results/${setId}`) });
    }
  };

  return (
    <div>
      <div className={styles.practiceHeader}>
        <div>
          <div className={styles.meta}>
            <Link to="/">Practice</Link> / {type.name}
          </div>
          <h1 style={{ fontSize: "1.5rem", margin: "0.25rem 0 0" }}>
            {type.name} <span className={styles.code}>{type.code}</span>
          </h1>
          <div className={styles.meta}>
            Question {position} of {total}
          </div>
        </div>
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <button type="button" className={styles.linkish} onClick={() => setShowTip((s) => !s)}>
            {showTip ? "Hide tip" : "Show tip"}
          </button>
          <button type="button" className={styles.linkish} onClick={finishEarly}>
            Finish set
          </button>
        </div>
      </div>

      <div className={styles.dots} aria-label="Progress">
        {Array.from({ length: total }, (_, i) => i + 1).map((n) => (
          <span
            key={n}
            className={n === position ? styles.dotCurrent : answeredPositions.has(n) ? styles.dotDone : styles.dot}
            aria-label={`Question ${n}${answeredPositions.has(n) ? ", answered" : ""}${n === position ? ", current" : ""}`}
          >
            {n}
          </span>
        ))}
      </div>

      <div className={styles.instructions}>
        {type.instructions}
        {showTip && (
          <p style={{ margin: "0.6rem 0 0" }}>
            <strong>Tip:</strong> {type.tip}
          </p>
        )}
      </div>

      {question.isLoading && <Loading label="Loading question…" />}
      {question.error && <ErrorMessage error={question.error} />}
      {question.data && (
        <QuestionRunner key={`${setId}-${position}`} type={type} question={question.data} isLast={isLast} onNext={goNext} />
      )}
    </div>
  );
}
