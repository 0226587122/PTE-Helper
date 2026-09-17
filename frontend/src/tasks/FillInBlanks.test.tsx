import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import type { BlankSegment, TaskResponse } from "../api/types";
import { question, taskType } from "../test/fixtures";
import ReadingFillBlanks from "./ReadingFillBlanks";
import ReadingWritingFillBlanks from "./ReadingWritingFillBlanks";
import type { TaskComponent } from "./types";

const dropdownSegments: BlankSegment[] = [
  "Rewilding may ",
  { blank: 0, options: ["reinforce", "reintroduce", "rearrange"] },
  " large animals and reduce the ",
  { blank: 1, options: ["rate", "risk", "rest"] },
  " of flooding.",
];

const dragSegments: BlankSegment[] = ["Rewilding may ", { blank: 0 }, " large animals and reduce the ", { blank: 1 }, " of flooding."];

function Harness({
  Component,
  segments,
  bank,
  review = false,
  initial = {},
  onResponse,
}: {
  Component: TaskComponent;
  segments: BlankSegment[];
  bank?: string[];
  review?: boolean;
  initial?: TaskResponse;
  onResponse?: (r: TaskResponse) => void;
}) {
  const [response, setResponse] = useState<TaskResponse>(initial);
  return (
    <Component
      type={taskType({ code: "RWFIB", audio: false, section: "reading" })}
      question={question({
        display: { segments, bank },
        answered: review,
        answer: review ? { blanks: ["reintroduce", "risk"] } : null,
      })}
      response={response}
      onChange={(r) => {
        setResponse(r);
        onResponse?.(r);
      }}
      locked={review}
      review={review}
      stage="answer"
      speaking={false}
    />
  );
}

describe("Reading & Writing Fill in the Blanks (dropdowns)", () => {
  it("records the option chosen for each blank", async () => {
    const user = userEvent.setup();
    const seen: TaskResponse[] = [];
    render(<Harness Component={ReadingWritingFillBlanks} segments={dropdownSegments} onResponse={(r) => seen.push(r)} />);

    await user.selectOptions(screen.getByRole("combobox", { name: "Blank 2" }), "risk");
    await user.selectOptions(screen.getByRole("combobox", { name: "Blank 1" }), "reintroduce");

    expect(seen.at(-1)).toEqual({ answers: ["reintroduce", "risk"] });
  });

  it("marks right and wrong blanks and shows the correct word in review", () => {
    render(
      <Harness Component={ReadingWritingFillBlanks} segments={dropdownSegments} review initial={{ answers: ["reinforce", "risk"] }} />,
    );
    expect(screen.getByRole("combobox", { name: "Blank 1" })).toBeDisabled();
    expect(screen.getByText("(reintroduce)")).toBeInTheDocument();
    expect(screen.queryByText("(risk)")).not.toBeInTheDocument();
  });
});

describe("Reading Fill in the Blanks (word bank)", () => {
  const bank = ["risk", "reintroduce", "remove", "success"];

  it("places a word by clicking it and then a blank, and removes it from the bank", async () => {
    const user = userEvent.setup();
    const seen: TaskResponse[] = [];
    render(<Harness Component={ReadingFillBlanks} segments={dragSegments} bank={bank} onResponse={(r) => seen.push(r)} />);

    const wordBank = screen.getByLabelText("Word bank");
    await user.click(within(wordBank).getByRole("button", { name: "reintroduce" }));
    await user.click(screen.getByRole("button", { name: "Blank 1" }));

    expect(seen.at(-1)).toEqual({ answers: ["reintroduce", null] });
    expect(within(wordBank).queryByRole("button", { name: "reintroduce" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Blank 1: reintroduce" })).toBeInTheDocument();
  });

  it("moves a word if it is placed in a second blank, and clears a blank when clicked", async () => {
    const user = userEvent.setup();
    const seen: TaskResponse[] = [];
    render(
      <Harness
        Component={ReadingFillBlanks}
        segments={dragSegments}
        bank={bank}
        initial={{ answers: ["risk", null] }}
        onResponse={(r) => seen.push(r)}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Blank 1: risk" }));
    expect(seen.at(-1)).toEqual({ answers: [null, null] });

    const wordBank = screen.getByLabelText("Word bank");
    await user.click(within(wordBank).getByRole("button", { name: "risk" }));
    await user.click(screen.getByRole("button", { name: "Blank 2" }));
    expect(seen.at(-1)).toEqual({ answers: [null, "risk"] });
  });
});
