import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAdminQuestion, useResolveReport, useUpdateQuestion } from "../api/hooks";
import { ErrorMessage, Loading } from "../components/Loading";
import styles from "./Admin.module.css";
import { StatusBadge } from "./AdminQuestions";

export default function AdminQuestion() {
  const id = Number(useParams().id);
  const question = useAdminQuestion(id);
  const update = useUpdateQuestion(id);
  const resolve = useResolveReport();
  const [draft, setDraft] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);

  useEffect(() => {
    if (question.data) setDraft(JSON.stringify(question.data.payload, null, 2));
  }, [question.data]);

  if (question.isLoading) return <Loading />;
  if (question.error) return <ErrorMessage error={question.error} />;
  const q = question.data!;
  const error = update.error as ApiError | null;

  const savePayload = () => {
    setParseError(null);
    let payload: Record<string, unknown>;
    try {
      payload = JSON.parse(draft);
    } catch {
      setParseError("That isn't valid JSON. Check for missing commas or quotes.");
      return;
    }
    update.mutate({ payload });
  };

  return (
    <>
      <p>
        <Link to="/admin/questions">← Back to questions</Link>
      </p>
      <div className={styles.panel}>
        <div className={styles.row}>
          <h2 style={{ margin: 0 }}>
            Question {q.id} <code>{q.task_type}</code>
          </h2>
          <StatusBadge status={q.status} />
          <span>Served {q.times_served} times</span>
          <span>{q.report_count} reports in total</span>
        </div>
        <div className={styles.row} style={{ marginTop: "0.75rem" }}>
          <label>
            Status{" "}
            <select value={q.status} onChange={(e) => update.mutate({ status: e.target.value })} disabled={update.isPending}>
              <option value="active">Active</option>
              <option value="backup">Backup</option>
              <option value="retired">Retired</option>
            </select>
          </label>
          <label>
            Difficulty{" "}
            <select
              value={q.difficulty ?? ""}
              onChange={(e) => e.target.value && update.mutate({ difficulty: Number(e.target.value) })}
              disabled={update.isPending}
            >
              <option value="">Not set</option>
              <option value="1">1 · Easier</option>
              <option value="2">2 · Standard</option>
              <option value="3">3 · Harder</option>
            </select>
          </label>
        </div>
        {update.isSuccess && (
          <p className={styles.success}>
            Saved.
            {update.data.promoted_ids.length > 0 && ` Promoted backup question ${update.data.promoted_ids.join(", ")} to keep the pool full.`}
          </p>
        )}
        {error && (
          <div className={styles.errors}>
            {error.message}
            {error.details.length > 0 && (
              <ul>
                {error.details.map((d) => (
                  <li key={d}>{d}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {q.source && (
        <div className={styles.panel}>
          <h3>
            Source: {q.source.title} <code>{q.source.source_key}</code> ({q.source.kind})
          </h3>
          <div className={styles.sourceBody}>{q.source.body}</div>
          {q.source.blank_markup && (
            <>
              <h4>Blank markup</h4>
              <div className={styles.sourceBody}>{q.source.blank_markup}</div>
            </>
          )}
          <p style={{ fontSize: "0.9rem", color: "var(--muted)" }}>
            This source is shared by every question that uses <code>{q.source.source_key}</code>.
          </p>
        </div>
      )}

      <div className={styles.panel}>
        <h3>Payload</h3>
        <p style={{ fontSize: "0.9rem", color: "var(--muted)" }}>
          Changes are checked with the same rules as the bank validator before they are saved.
        </p>
        <textarea aria-label="Payload JSON" className={styles.editor} value={draft} onChange={(e) => setDraft(e.target.value)} spellCheck={false} />
        {parseError && <p className={styles.errors}>{parseError}</p>}
        <div className={styles.row} style={{ marginTop: "0.5rem" }}>
          <button type="button" className={styles.buttonPrimary} onClick={savePayload} disabled={update.isPending}>
            Save payload
          </button>
          <button type="button" className={styles.button} onClick={() => setDraft(JSON.stringify(q.payload, null, 2))}>
            Reset
          </button>
        </div>
      </div>

      <div className={styles.panel}>
        <h3>Reports</h3>
        {q.reports.length === 0 && <p>No reports.</p>}
        {q.reports.length > 0 && (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Date</th>
                <th>Reason</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {q.reports.map((r) => (
                <tr key={r.id}>
                  <td>{new Date(r.created_at + "Z").toLocaleString()}</td>
                  <td>{r.reason}</td>
                  <td>
                    {r.resolved_at ? (
                      "Resolved"
                    ) : (
                      <button type="button" className={styles.button} onClick={() => resolve.mutate(r.id)} disabled={resolve.isPending}>
                        Mark resolved
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
