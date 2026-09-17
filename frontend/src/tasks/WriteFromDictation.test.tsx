import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import type { TaskResponse } from "../api/types";
import { question, taskType } from "../test/fixtures";
import type { Stage } from "./types";
import WriteFromDictation from "./WriteFromDictation";

function Harness({ stage = "answer", locked = false, review = false, speaking = false, onResponse }: {
  stage?: Stage;
  locked?: boolean;
  review?: boolean;
  speaking?: boolean;
  onResponse?: (r: TaskResponse) => void;
}) {
  const [response, setResponse] = useState<TaskResponse>(review ? { text: "most students submit online" } : {});
  return (
    <WriteFromDictation
      type={taskType()}
      question={question({
        display: { audio: "Most students submit their assignments online before the deadline." },
        answered: review,
        answer: review ? { sentence: "Most students submit their assignments online before the deadline." } : null,
      })}
      response={response}
      onChange={(r) => {
        setResponse(r);
        onResponse?.(r);
      }}
      locked={locked}
      review={review}
      stage={stage}
      speaking={speaking}
    />
  );
}

describe("WriteFromDictation", () => {
  it("records what the student types", async () => {
    const user = userEvent.setup();
    const seen: TaskResponse[] = [];
    render(<Harness onResponse={(r) => seen.push(r)} />);
    await user.type(screen.getByLabelText("Type the sentence you hear"), "Most students");
    expect(seen.at(-1)).toEqual({ text: "Most students" });
  });

  it("never shows the sentence before the answer is marked", () => {
    render(<Harness />);
    expect(screen.queryByText(/before the deadline/)).not.toBeInTheDocument();
  });

  it("shows the audio status while playing", () => {
    render(<Harness stage="audio" speaking />);
    expect(screen.getByText(/Playing/)).toBeInTheDocument();
  });

  it("locks the box when time is up", () => {
    render(<Harness locked />);
    expect(screen.getByLabelText("Type the sentence you hear")).toBeDisabled();
  });

  it("shows the correct sentence in review", () => {
    render(<Harness review locked />);
    expect(screen.getByText("Most students submit their assignments online before the deadline.")).toBeInTheDocument();
    expect(screen.getByLabelText("Type the sentence you hear")).toHaveValue("most students submit online");
  });
});
