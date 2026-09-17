import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import type { TaskResponse } from "../api/types";
import { question, taskType } from "../test/fixtures";
import ReorderParagraphs from "./ReorderParagraphs";
import type { TaskProps } from "./types";

const paragraphs = [
  { id: "C", text: "Consequently, ideas spread quickly." },
  { id: "A", text: "The printing press was developed in Europe." },
  { id: "B", text: "Printing reduced the cost of books." },
];

function Harness(props: Partial<TaskProps> & { initial?: TaskResponse; onResponse?: (r: TaskResponse) => void }) {
  const [response, setResponse] = useState<TaskResponse>(props.initial ?? {});
  return (
    <ReorderParagraphs
      type={taskType({ code: "RO", audio: false })}
      question={question({ display: { paragraphs }, ...props.question })}
      response={response}
      onChange={(r) => {
        setResponse(r);
        props.onResponse?.(r);
      }}
      locked={props.locked ?? false}
      review={props.review ?? false}
      stage="answer"
      speaking={false}
    />
  );
}

describe("ReorderParagraphs", () => {
  it("moves paragraphs into the answer column in the chosen order", async () => {
    const user = userEvent.setup();
    const seen: TaskResponse[] = [];
    render(<Harness onResponse={(r) => seen.push(r)} />);

    await user.click(screen.getByRole("button", { name: "Move paragraph A to your answer" }));
    await user.click(screen.getByRole("button", { name: "Move paragraph B to your answer" }));
    await user.click(screen.getByRole("button", { name: "Move paragraph C to your answer" }));

    expect(seen.at(-1)).toEqual({ order: ["A", "B", "C"] });
    const target = screen.getByRole("region", { name: "Target" });
    expect(within(target).getByTestId("target-A")).toHaveTextContent("printing press");
    expect(screen.getByText("All paragraphs placed.")).toBeInTheDocument();
  });

  it("reorders with the up and down buttons and can move a paragraph back", async () => {
    const user = userEvent.setup();
    const seen: TaskResponse[] = [];
    render(<Harness initial={{ order: ["B", "A", "C"] }} onResponse={(r) => seen.push(r)} />);

    await user.click(screen.getByRole("button", { name: "Move paragraph A up" }));
    expect(seen.at(-1)).toEqual({ order: ["A", "B", "C"] });

    await user.click(screen.getByRole("button", { name: "Move paragraph C back" }));
    expect(seen.at(-1)).toEqual({ order: ["A", "B"] });
    expect(within(screen.getByRole("region", { name: "Source" })).getByTestId("source-C")).toBeInTheDocument();
  });

  it("disables every control when locked", () => {
    render(<Harness initial={{ order: ["A"] }} locked />);
    for (const button of screen.getAllByRole("button")) expect(button).toBeDisabled();
  });

  it("shows which neighbouring pairs are correct in review", () => {
    render(
      <Harness
        initial={{ order: ["A", "C", "B"] }}
        locked
        review
        question={question({ display: { paragraphs }, answered: true, answer: { order: ["A", "B", "C"] } })}
      />,
    );
    expect(screen.getAllByText(/doesn't follow this one/)).toHaveLength(2);
    const correct = screen.getByText("Correct order:").parentElement!;
    expect(within(correct).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "The printing press was developed in Europe.",
      "Printing reduced the cost of books.",
      "Consequently, ideas spread quickly.",
    ]);
  });
});
