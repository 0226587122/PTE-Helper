import { Link, useParams } from "react-router-dom";

import { useMockReport, useReview, useTaskTypes } from "../api/hooks";
import type { SkillScore } from "../api/types";
import { ErrorMessage, Loading } from "../components/Loading";
import { ResultPanel } from "../components/ResultPanel";
import { bandFor } from "../pages/Home";
import { TASKS } from "../tasks";
import styles from "./Mock.module.css";

function SkillCard({ skill }: { skill: SkillScore }) {
  return (
    <div className={styles.skillCard}>
      <div className={styles.skillName}>{skill.label}</div>
      {skill.score === null ? (
        <div className={styles.unavailable}>{skill.note ?? "Not scored"}</div>
      ) : (
        <>
          <div className={styles.skillScore}>{skill.score}</div>
          <div className={styles.bar}>
            <div className={styles.barFill} style={{ width: `${((skill.score - 10) / 80) * 100}%` }} />
          </div>
          {skill.item_count !== undefined && (
            <div className={styles.unavailable}>
              {skill.item_count} question{skill.item_count === 1 ? "" : "s"}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/** The score report for a finished mock test, with every answer reviewable. */
export default function MockReportPage() {
  const setId = Number(useParams().setId);
  const report = useMockReport(setId);
  const review = useReview(setId);
  const types = useTaskTypes();

  if (report.isLoading || types.isLoading) return <Loading label="Marking your mock test…" />;
  if (report.error) return <ErrorMessage error={report.error} />;
  const data = report.data!;
  const minutes =
    data.started_at && data.finished_at
      ? Math.round((new Date(data.finished_at).getTime() - new Date(data.started_at).getTime()) / 60000)
      : null;

  return (
    <div>
      <section className={styles.reportHero}>
        <div>
          <div className={styles.heroText}>{data.overall_label ?? "Estimated overall"}</div>
          <div className={styles.overall}>
            {data.overall_score}
            <span style={{ fontSize: "1.2rem", fontWeight: 600 }}> / 90</span>
          </div>
          <div>{bandFor(data.overall_score).label}</div>
        </div>
        <div>
          <h1>Full mock test</h1>
          <p className={styles.heroText}>
            You answered {data.answered_count} of {data.item_count} questions
            {data.late_count > 0 ? `, and ${data.late_count} ran out of time` : ""}
            {minutes !== null ? `, over ${minutes} minutes` : ""}.
          </p>
        </div>
      </section>

      <div className={styles.disclaimer}>{data.disclaimer}</div>

      <h2>Communicative skills</h2>
      <div className={styles.skillGrid}>
        {data.communicative_skills.map((skill) => (
          <SkillCard key={skill.key} skill={skill} />
        ))}
      </div>

      <h2>Enabling skills</h2>
      <div className={styles.skillGrid}>
        {data.enabling_skills.map((skill) => (
          <SkillCard key={skill.key} skill={skill} />
        ))}
      </div>

      <h2>Parts</h2>
      <table className={styles.sectionTable}>
        <thead>
          <tr>
            <th>Part</th>
            <th>Practice estimate</th>
            <th>Average</th>
            <th>Answered</th>
          </tr>
        </thead>
        <tbody>
          {data.sections.map((section) => (
            <tr key={section.section}>
              <td>{section.label}</td>
              <td>{section.score ?? "–"}</td>
              <td>{section.percent === null ? "–" : `${Math.round(section.percent)}%`}</td>
              <td>
                {section.answered_count} of {section.item_count}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
        <Link to="/">Back to practice</Link>
        <Link to="/mock">Start another mock test</Link>
      </div>

      <h2>Review your answers</h2>
      {review.error && <ErrorMessage error={review.error} />}
      {review.data?.map((question) => {
        const type = types.data?.find((t) => t.code === question.task_type);
        if (!type) return null;
        const Task = TASKS[type.code];
        return (
          <details key={question.position} className={styles.reviewItem}>
            <summary>
              <span>
                {question.position}. {type.name}
              </span>
              <span>
                {question.answered ? `${Math.round(question.result?.pct ?? 0)}%` : <span className={styles.lateFlag}>Not answered</span>}
              </span>
            </summary>
            <div className={styles.reviewBody}>
              {question.answered ? (
                <>
                  <Task
                    type={type}
                    question={question}
                    response={question.response ?? {}}
                    onChange={() => {}}
                    locked
                    review
                    stage="done"
                    speaking={false}
                  />
                  <ResultPanel question={question} type={type} showTip={false} />
                </>
              ) : (
                <p className={styles.unavailable}>
                  This question wasn't answered in time, so it scored zero, exactly as it would in the real test.
                </p>
              )}
            </div>
          </details>
        );
      })}
    </div>
  );
}
