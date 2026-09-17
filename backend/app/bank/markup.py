"""Blank markup used by reading passages.

A blank is written as ``{{correct|distractor one|distractor two|distractor three}}``. The first option is always
the correct answer; the order shown to students is shuffled when a set is drawn.
"""

import re
from dataclasses import dataclass

BLANK_RE = re.compile(r"\{\{([^{}]+)\}\}")


class MarkupError(ValueError):
    pass


@dataclass
class Blank:
    correct: str
    distractors: list[str]


def parse(markup: str) -> tuple[list[str | int], list[Blank]]:
    """Split markup into text pieces and blank numbers, plus the blanks themselves."""
    if markup.count("{{") != markup.count("}}"):
        raise MarkupError("Unbalanced {{ }} in blank markup.")
    segments: list[str | int] = []
    blanks: list[Blank] = []
    position = 0
    for match in BLANK_RE.finditer(markup):
        if match.start() > position:
            segments.append(markup[position : match.start()])
        options = [o.strip() for o in match.group(1).split("|")]
        if any(not o for o in options):
            raise MarkupError(f"Empty option in blank '{match.group(0)}'.")
        if len({o.lower() for o in options}) != len(options):
            raise MarkupError(f"Duplicate options in blank '{match.group(0)}'.")
        segments.append(len(blanks))
        blanks.append(Blank(correct=options[0], distractors=options[1:]))
        position = match.end()
    if position < len(markup):
        segments.append(markup[position:])
    leftover = "".join(s for s in segments if isinstance(s, str))
    if "{" in leftover or "}" in leftover:
        raise MarkupError("Stray brace outside a blank.")
    return segments, blanks


def fill(markup: str) -> str:
    """The passage with every blank filled with its correct answer."""
    return BLANK_RE.sub(lambda m: m.group(1).split("|")[0].strip(), markup)
