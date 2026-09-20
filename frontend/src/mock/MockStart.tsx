import { useCallback, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useBlueprint, useStartMock } from "../api/hooks";
import { ErrorMessage, Loading } from "../components/Loading";
import { EquipmentCheck } from "./EquipmentCheck";
import styles from "./Mock.module.css";

/** What the mock test involves, an equipment check, then start. */
export default function MockStart() {
  const blueprint = useBlueprint();
  const start = useStartMock();
  const navigate = useNavigate();
  const [ready, setReady] = useState(false);
  const onReady = useCallback((value: boolean) => setReady(value), []);

  if (blueprint.isLoading) return <Loading />;
  if (blueprint.error) return <ErrorMessage error={blueprint.error} />;
  const plan = blueprint.data!;

  return (
    <div className={styles.card}>
      <h1>Full mock test</h1>
      <p>
        All three parts of the PTE Academic test, one after the other, with the same timing as the real exam. You will
        not see any scores until the end.
      </p>
      <p>
        <strong>
          About {plan.minutes.min} to {plan.minutes.max} minutes
        </strong>{" "}
        and {plan.items.min} to {plan.items.max} questions, plus an unscored spoken introduction.
      </p>

      <ol className={styles.partList}>
        {plan.parts.map((part) => (
          <li key={part.section} className={styles.partItem}>
            <h3>{part.title}</h3>
            <div className={styles.types}>
              {part.minutes.min === part.minutes.max
                ? `${part.minutes.min} minutes`
                : `about ${part.minutes.min} to ${part.minutes.max} minutes`}{" "}
              · {part.task_types.map((t) => t.name).join(", ")}
            </div>
          </li>
        ))}
      </ol>

      <div className={styles.warning}>
        Once you start, the clock runs like the real test. It keeps running if you close the tab or walk away, and any
        question whose time runs out scores zero. Set aside the full time before you begin.
      </div>

      <EquipmentCheck onReady={onReady} />

      {start.error && <p className={styles.bad}>{(start.error as ApiError).message}</p>}

      <div className={styles.checkRow} style={{ marginTop: "1.5rem" }}>
        <button
          type="button"
          className={styles.primary}
          disabled={start.isPending}
          onClick={() => start.mutate(undefined, { onSuccess: (state) => navigate(`/mock/${state.id}`) })}
        >
          {start.isPending ? "Preparing your test…" : ready ? "Start the mock test" : "Start anyway"}
        </button>
        <Link to="/">Back to practice</Link>
      </div>
      {!ready && <p className={styles.saveNote}>Finish both checks above for the full exam experience.</p>}
    </div>
  );
}
