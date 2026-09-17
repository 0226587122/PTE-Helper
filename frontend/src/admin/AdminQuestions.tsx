import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAdminQuestions, useTaskTypes } from "../api/hooks";
import { ErrorMessage, Loading } from "../components/Loading";
import styles from "./Admin.module.css";

export function StatusBadge({ status }: { status: string }) {
  const className = status === "active" ? styles.statusActive : status === "backup" ? styles.statusBackup : styles.statusRetired;
  return <span className={className}>{status}</span>;
}

export default function AdminQuestions() {
  const [params, setParams] = useSearchParams();
  const types = useTaskTypes();
  const [search, setSearch] = useState(params.get("search") ?? "");
  const filters = {
    task_type: params.get("task_type") ?? "",
    status: params.get("status") ?? "",
    reported: params.get("reported") === "true",
    search: params.get("search") ?? "",
    page: Number(params.get("page") ?? 1),
  };
  const questions = useAdminQuestions(filters);

  const update = (changes: Record<string, string>) => {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (!("page" in changes)) next.delete("page");
    setParams(next);
  };

  const pages = questions.data ? Math.max(1, Math.ceil(questions.data.total / questions.data.page_size)) : 1;

  return (
    <>
      <div className={styles.filters}>
        <select aria-label="Task type" value={filters.task_type} onChange={(e) => update({ task_type: e.target.value })}>
          <option value="">All types</option>
          {types.data?.map((t) => (
            <option key={t.code} value={t.code}>
              {t.code} · {t.name}
            </option>
          ))}
        </select>
        <select aria-label="Status" value={filters.status} onChange={(e) => update({ status: e.target.value })}>
          <option value="">Any status</option>
          <option value="active">Active</option>
          <option value="backup">Backup</option>
          <option value="retired">Retired</option>
        </select>
        <label>
          <input type="checkbox" checked={filters.reported} onChange={(e) => update({ reported: e.target.checked ? "true" : "" })} />{" "}
          Open reports only
        </label>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            update({ search });
          }}
        >
          <input aria-label="Search" placeholder="Search text or source key" value={search} onChange={(e) => setSearch(e.target.value)} />
        </form>
      </div>

      {questions.isLoading && <Loading />}
      {questions.error && <ErrorMessage error={questions.error} />}
      {questions.data && (
        <>
          <p className={styles.row}>{questions.data.total} questions</p>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Preview</th>
                  <th>Served</th>
                  <th>Reports</th>
                </tr>
              </thead>
              <tbody>
                {questions.data.items.map((q) => (
                  <tr key={q.id}>
                    <td>
                      <Link to={`/admin/questions/${q.id}`}>{q.id}</Link>
                    </td>
                    <td>
                      <code>{q.task_type}</code>
                    </td>
                    <td>
                      <StatusBadge status={q.status} />
                    </td>
                    <td>
                      <Link to={`/admin/questions/${q.id}`}>{q.preview || q.source_key}</Link>
                    </td>
                    <td>{q.times_served}</td>
                    <td className={q.open_reports ? styles.low : undefined}>
                      {q.open_reports} open / {q.report_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className={styles.pager}>
            <button type="button" className={styles.button} disabled={filters.page <= 1} onClick={() => update({ page: String(filters.page - 1) })}>
              Previous
            </button>
            <span>
              Page {filters.page} of {pages}
            </span>
            <button type="button" className={styles.button} disabled={filters.page >= pages} onClick={() => update({ page: String(filters.page + 1) })}>
              Next
            </button>
          </div>
        </>
      )}
    </>
  );
}
