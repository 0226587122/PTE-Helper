import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { useBlueprint, useMockQuestion, useMockState, useSubmitMock, useTaskTypes } from "../api/hooks";
import { ErrorMessage, Loading } from "../components/Loading";
import { MockHeader } from "./MockHeader";
import { MockItem } from "./MockItem";
import styles from "./Mock.module.css";
import { PartIntro } from "./PartIntro";
import { PersonalIntroduction } from "./PersonalIntroduction";
import { useServerClock } from "./useServerClock";

const MIN_WIDTH = 1024;

/** Runs a full mock test: the introduction, then all three parts back to back. */
export default function MockRunner() {
  const setId = Number(useParams().setId);
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const state = useMockState(setId);
  const blueprint = useBlueprint();
  const types = useTaskTypes();
  const submit = useSubmitMock(setId);

  const [showIntro, setShowIntro] = useState(true);
  const [partStarted, setPartStarted] = useState<string | null>(null);
  const [narrow, setNarrow] = useState(window.innerWidth < MIN_WIDTH);

  useEffect(() => {
    const onResize = () => setNarrow(window.innerWidth < MIN_WIDTH);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // Warn before a refresh or a closed tab, because the clock keeps running.
  useEffect(() => {
    const onBeforeUnload = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, []);

  const position = Number(params.get("q")) || 0;
  const question = useMockQuestion(setId, position);

  // Resume where the student left off, or start at the first question.
  useEffect(() => {
    if (!state.data || position) return;
    setParams({ q: String(state.data.current_position) }, { replace: true });
  }, [state.data, position, setParams]);

  // A finished test goes straight to its report.
  useEffect(() => {
    if (state.data?.status === "finished") navigate(`/mock/${setId}/report`, { replace: true });
  }, [state.data?.status, navigate, setId]);

  const itemRemaining = useServerClock(question.data?.deadline_at ?? null, question.data?.server_time ?? null);
  const sectionRemaining = useServerClock(
    question.data?.section_deadline_at ?? null,
    question.data?.server_time ?? null,
  );

  if (state.isLoading || blueprint.isLoading || types.isLoading || !position) return <Loading label="Opening your mock test…" />;
  if (state.error) return <ErrorMessage error={state.error} />;
  if (!state.data || !blueprint.data) return <ErrorMessage error={new Error("We couldn't open this mock test.")} />;

  if (narrow) {
    return (
      <div className={styles.card}>
        <h1>Use a larger screen for the mock test</h1>
        <p>
          The mock test copies the real exam layout, which needs a screen at least {MIN_WIDTH} pixels wide. Please use a
          laptop or desktop computer. Single task drills work on a phone.
        </p>
        <button type="button" className={styles.secondary} onClick={() => navigate("/")}>
          Back to practice
        </button>
      </div>
    );
  }

  if (showIntro && state.data.answered_count === 0 && position === 1) {
    return (
      <PersonalIntroduction blueprint={blueprint.data.personal_introduction} onDone={() => setShowIntro(false)} />
    );
  }

  if (question.error) {
    const error = question.error as ApiError;
    return (
      <div className={styles.card}>
        <h1>That question isn't available</h1>
        <p>{error.message}</p>
        <button
          type="button"
          className={styles.primary}
          onClick={() => setParams({ q: String(state.data!.current_position) }, { replace: true })}
        >
          Go to my current question
        </button>
      </div>
    );
  }
  if (!question.data) return <Loading label="Loading question…" />;

  const item = question.data;
  const type = types.data?.find((t) => t.code === item.task_type);
  const part = blueprint.data.parts.find((p) => p.section === item.section);
  if (!type || !part) return <ErrorMessage error={new Error("We couldn't load this question type.")} />;

  // Show the part instructions the first time the student reaches each part.
  if (item.starts_part && partStarted !== item.section && !item.answered) {
    return <PartIntro part={part} onStart={() => setPartStarted(item.section)} />;
  }

  const firstOfPart = state.data.items.find((i) => i.section === item.section)?.position ?? 1;

  return (
    <div className={styles.shell}>
      <MockHeader
        partTitle={part.title}
        taskName={type.name}
        position={item.position}
        total={state.data.question_count}
        sectionRemaining={sectionRemaining}
        itemRemaining={item.allow_back ? null : itemRemaining}
      />
      <main className={styles.main}>
        <MockItem
          key={item.position}
          question={item}
          type={type}
          secondsRemaining={item.allow_back ? sectionRemaining : itemRemaining}
          canGoBack={item.allow_back && item.position > firstOfPart}
          onMoved={(next) => {
            setParams({ q: String(next) });
            window.scrollTo({ top: 0 });
          }}
          onFinished={() => navigate(`/mock/${setId}/report`, { replace: true })}
          onExit={() => {
            if (
              window.confirm(
                "Leave the mock test? The clock keeps running while you are away, so any question whose time runs out will score zero.",
              )
            ) {
              navigate("/");
            }
          }}
        />
        {submit.error && <ErrorMessage error={submit.error} />}
      </main>
    </div>
  );
}
