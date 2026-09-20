import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MockHeader } from "./MockHeader";

describe("MockHeader", () => {
  const base = {
    partTitle: "Part 2: Reading",
    taskName: "Reorder Paragraphs",
    position: 12,
    total: 68,
    sectionRemaining: 900,
    itemRemaining: null,
  };

  it("shows the part, task, item counter and part clock", () => {
    render(<MockHeader {...base} />);
    expect(screen.getByText("Part 2: Reading")).toBeInTheDocument();
    expect(screen.getByText("Reorder Paragraphs")).toBeInTheDocument();
    expect(screen.getByText("Question 12 of 68")).toBeInTheDocument();
    expect(screen.getByText("15:00")).toBeInTheDocument();
  });

  it("shows both clocks when an item has its own deadline", () => {
    render(<MockHeader {...base} sectionRemaining={null} itemRemaining={95} />);
    expect(screen.getByText("1:35")).toBeInTheDocument();
    expect(screen.queryByText("Part time left")).not.toBeInTheDocument();
  });

  it("announces the five minute, one minute and ten second warnings", () => {
    const { rerender } = render(<MockHeader {...base} sectionRemaining={300} />);
    expect(screen.getByText("5:00 left in this part")).toBeInTheDocument();
    rerender(<MockHeader {...base} sectionRemaining={60} />);
    expect(screen.getByText("1:00 left in this part")).toBeInTheDocument();
    rerender(<MockHeader {...base} sectionRemaining={10} />);
    expect(screen.getByText("0:10 left in this part")).toBeInTheDocument();
  });

  it("does not announce anything in the middle of a part", () => {
    render(<MockHeader {...base} sectionRemaining={842} />);
    expect(screen.queryByText(/left in this part/)).not.toBeInTheDocument();
  });
});
