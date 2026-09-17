import { useState } from "react";

import { ApiError } from "../api/client";
import { useFeedback, useReport } from "../api/hooks";
import type { Feedback, Question, TaskType } from "../api/types";
import styles from "./Runner.module.css";

function ringColour(pct: number) {
  if (pct >= 79) return "#bbf7d0";
  if (pct >= 50) return "#bfdbfe";
  if (pct >= 30) return "#fde68a";
  return "#fecaca";
}

const TRAIT_NAMES: Record<string, string> = {
  form: "Form",
  content: "Content",
  grammar: "Grammar",
  vocabulary: "Vocabulary",
  structure: "Structure",
  linguistic_range: "Linguistic range",
  fluency: "Fluency",
  pronunciation: "Pronunciation",
};

function DetailSummary({ question }: { question: Question }) {
  const detail = (question.result?.detail ?? {}) as Record<string, unknown>;
  const traits = detail.traits as Record<string, number> | undefined;
  const items: string[] = [];
  if (typeof detail.words_matched === "number") items.push(`${detail.words_matched} of ${detail.words_total} words`);
  if (typeof detail.word_count === "number") items.push(`${detail.word_count} words`);
  if (typeof detail.correct_selected === "number") {
    items.push(`${detail.correct_selected} correct choice(s)`);
    if (Number(detail.incorrect_selected) > 0) items.push(`${detail.incorrect_selected} wrong choice(s), minus one each`);
  }
  if (Array.isArray(detail.per_blank)) items.push(`${detail.per_blank.filter(Boolean).length} of ${detail.per_blank.length} blanks`);
  if (Array.isArray(detail.correct_pairs)) items.push(`${detail.correct_pairs.length} correct pair(s)`);
  if (traits) {
    const isPercent = "fluency" in traits;
    for (const [key, value] of Object.entries(traits)) {
      items.push(`${TRAIT_NAMES[key] ?? key}: ${value}${isPercent ? "%" : ""}`);
    }
  }
  if (!items.length) return null;
  return (
    <ul className={styles.traits}>
      {items.map((item) => (
        <li key={item} className={styles.trait}>
          {item}
        </li>
      ))}
    </ul>
  );
}

function FeedbackView({ feedback }: { feedback: Feedback }) {
  return (
    <div>
      <p>
        <strong>Examiner estimate: {feedback.score}/90</strong>{" "}
        <span className={styles.muted}>(practice estimate, not an official Pearson score)</span>
      </p>
      <table className={styles.traitTable}>
        <thead>
          <tr>
            <th>Trait</th>
            <th>Score</th>
            <th>Comment</th>
          </tr>
        </thead>
        <tbody>
          {feedback.traits.map((t) => (
            <tr key={t.name}>
              <td>{t.name}</td>
              <td>
                {t.score}/{t.max}
              </td>
              <td>{t.comment}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className={styles.feedbackGrid}>
        <div>
          <strong>What went well</strong>
          <ul className={styles.feedbackList}>
            {feedback.strengths.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
        <div>
          <strong>How to improve</strong>
          <ul className={styles.feedbackList}>
            {feedback.improvements.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      </div>
      <p>
        <strong>Model answer</strong>
      </p>
      <div className={styles.modelAnswer}>{feedback.model_answer}</div>
    </div>
  );
}

function FeedbackSection({ question }: { question: Question }) {
  const request = useFeedback(question.set_question_id);
  const feedback = request.data ?? question.feedback;
  return (
    <div className={styles.feedback}>
      {feedback ? (
        <FeedbackView feedback={feedback} />
      ) : (
        <>
          <button type="button" className={styles.secondary} onClick={() => request.mutate()} disabled={request.isPending}>
            {request.isPending ? "Getting feedback… this can take up to a minute" : "Get examiner feedback"}
          </button>
          <p className={styles.muted}>Claude reviews your answer like a PTE examiner and suggests how to improve.</p>
          {request.error && <p className={styles.error}>{(request.error as ApiError).message}</p>}
        </>
      )}
    </div>
  );
}

const REASONS = [
  "The audio or text has a mistake",
  "The correct answer seems wrong",
  "More than one answer could be correct",
  "The question is confusing",
  "Something else",
];

export function ReportLink({ questionId }: { questionId: number }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState(REASONS[0]);
  const [details, setDetails] = useState("");
  const report = useReport(questionId);

  if (report.isSuccess) return <p className={styles.muted}>{report.data.message}</p>;
  return (
    <div className={styles.report}>
      {!open ? (
        <button type="button" className={styles.linkButton} onClick={() => setOpen(true)}>
          Report this question
        </button>
      ) : (
        <form
          className={styles.reportForm}
          onSubmit={(e) => {
            e.preventDefault();
            report.mutate(details.trim() ? `${reason}: ${details.trim()}` : reason);
          }}
        >
          <label htmlFor={`reason-${questionId}`}>What's wrong with this question?</label>
          <select id={`reason-${questionId}`} value={reason} onChange={(e) => setReason(e.target.value)}>
            {REASONS.map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
          <textarea
            aria-label="More details (optional)"
            placeholder="More details (optional)"
            maxLength={400}
            value={details}
            onChange={(e) => setDetails(e.target.value)}
          />
          <div className={styles.actions} style={{ margin: 0 }}>
            <button type="submit" className={styles.secondary} disabled={report.isPending}>
              Send report
            </button>
            <button type="button" className={styles.linkButton} onClick={() => setOpen(false)}>
              Cancel
            </button>
          </div>
          {report.error && <p className={styles.error}>{(report.error as ApiError).message}</p>}
        </form>
      )}
    </div>
  );
}

export function ResultPanel({ question, type, showTip = true }: { question: Question; type: TaskType; showTip?: boolean }) {
  const result = question.result;
  if (!result) return null;
  return (
    <section className={styles.result} aria-label="Your score">
      <div className={styles.resultHeader}>
        <div className={styles.scoreRing} style={{ background: ringColour(result.pct) }}>
          {Math.round(result.pct)}%
        </div>
        <div>
          <div>
            <strong>Practice score</strong>
          </div>
          <div className={styles.scoreCaption}>
            {Number.isInteger(result.max_score) && result.max_score !== 100
              ? `${result.score} out of ${result.max_score}. `
              : ""}
            This is a practice estimate, not an official Pearson result.
          </div>
          <DetailSummary question={question} />
        </div>
      </div>
      {result.zeroed_reason && <div className={styles.warning}>{result.zeroed_reason}</div>}
      {showTip && (
        <div className={styles.tip}>
          <strong>Tip:</strong> {type.tip}
        </div>
      )}
      {type.ai_feedback && <FeedbackSection question={question} />}
      <ReportLink questionId={question.question_id} />
    </section>
  );
}
