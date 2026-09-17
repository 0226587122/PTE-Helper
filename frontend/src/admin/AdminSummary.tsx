import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAdminSummary, usePromoteBackup } from "../api/hooks";
import { ErrorMessage, Loading } from "../components/Loading";
import styles from "./Admin.module.css";

const MIN_ACTIVE = 30;

export default function AdminSummary() {
  const summary = useAdminSummary();
  const promote = usePromoteBackup();

  if (summary.isLoading) return <Loading />;
  if (summary.error) return <ErrorMessage error={summary.error} />;

  return (
    <>
      <p>
        Practice sets draw from active questions and top up from backups. When a question is retired, the oldest backup
        is promoted automatically to keep at least {MIN_ACTIVE} active questions per type.
      </p>
      {promote.error && <p className={styles.errors}>{(promote.error as ApiError).message}</p>}
      {promote.isSuccess && <p className={styles.success}>Promoted question {promote.data.id} to active.</p>}
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Type</th>
              <th>Active</th>
              <th>Backup</th>
              <th>Retired</th>
              <th>Open reports</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {summary.data?.map((row) => (
              <tr key={row.code}>
                <td>
                  <Link to={`/admin/questions?task_type=${row.code}`}>{row.name}</Link> <code>{row.code}</code>
                </td>
                <td className={row.active < MIN_ACTIVE ? styles.low : undefined}>{row.active}</td>
                <td className={row.backup === 0 ? styles.low : undefined}>{row.backup}</td>
                <td>{row.retired}</td>
                <td>
                  {row.open_reports > 0 ? (
                    <Link to={`/admin/questions?task_type=${row.code}&reported=true`}>{row.open_reports}</Link>
                  ) : (
                    0
                  )}
                </td>
                <td>
                  <button
                    type="button"
                    className={styles.button}
                    disabled={row.backup === 0 || promote.isPending}
                    onClick={() => promote.mutate(row.code)}
                  >
                    Promote oldest backup
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
