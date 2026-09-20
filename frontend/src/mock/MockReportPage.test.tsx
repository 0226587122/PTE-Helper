import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import type { SpellingSkillDetail } from "../api/types";
import { SpellingWords } from "./MockReportPage";

const detail = (words: SpellingSkillDetail["misspelled_words"]): SpellingSkillDetail => ({
  error_count: words.length,
  words_checked: 240,
  errors_per_hundred: 1.3,
  misspelled_words: words,
});

describe("the spelling section of the report", () => {
  it("lists each misspelled word with what it looked like you meant", () => {
    render(
      <SpellingWords
        detail={detail([
          { typed: "recieve", intended: "receive" },
          { typed: "seperate", intended: "separate" },
        ])}
      />,
    );
    expect(screen.getByText("recieve")).toBeInTheDocument();
    expect(screen.getByText(/receive/)).toBeInTheDocument();
    expect(screen.getByText("seperate")).toBeInTheDocument();
  });

  it("still shows a word when there is no guess at what was meant", () => {
    render(<SpellingWords detail={detail([{ typed: "qwertyx", intended: null }])} />);
    expect(screen.getByText("qwertyx")).toBeInTheDocument();
  });

  it("says nothing at all when the spelling was clean", () => {
    const { container } = render(<SpellingWords detail={detail([])} />);
    expect(container).toBeEmptyDOMElement();
  });
});
