"""Turning a spelling check into a trait score and a skill percentage.

A misspelling costs a student once. In the writing tasks it lowers the Spelling trait, which is part
of that item's score. In Write from Dictation and the listening blanks the word was already marked
wrong by the answer key, so nothing further is deducted there - the misspelling is only *recorded*,
so the Spelling enabling skill can see it. Nothing is deducted twice for the same word.
"""

from typing import Any

from app.config import get_settings
from app.spelling.checker import SpellingCheck, check, intended_word, near_miss

__all__ = [
    "SpellingCheck",
    "check",
    "intended_word",
    "near_miss",
    "skill_percent",
    "spelling_detail",
    "trait",
]


def trait(errors_per_hundred: float | None) -> int:
    """The writing Spelling trait, 0 to 2. Nothing typed scores 0, as an empty answer does."""
    if errors_per_hundred is None:
        return 0
    settings = get_settings()
    if errors_per_hundred <= settings.spelling_good_per_hundred:
        return 2
    if errors_per_hundred <= settings.spelling_fair_per_hundred:
        return 1
    return 0


def skill_percent(error_count: int, typed_words: int) -> float | None:
    """The Spelling enabling skill as a percentage, from the error rate over everything typed.

    Clean spelling is 100%. The rate at which it reaches zero is a setting rather than a guess
    buried in the code, because it is the one number here with no published equivalent.
    """
    if typed_words <= 0:
        return None
    per_hundred = error_count / typed_words * 100
    zero_at = get_settings().spelling_zero_per_hundred
    if zero_at <= 0:  # pragma: no cover - a misconfiguration, not a real setting
        return 100.0 if per_hundred == 0 else 0.0
    return round(max(0.0, min(100.0, (1 - per_hundred / zero_at) * 100)), 1)


def spelling_detail(result: SpellingCheck) -> dict[str, Any]:
    """The part of an item's score detail that the report reads spelling out of."""
    return {
        "typed_words": result.typed_words,
        "error_count": result.error_count,
        "errors_per_hundred": result.errors_per_hundred,
        # Each distinct misspelling once, with what it was probably meant to be.
        "misspellings": result.misspellings,
    }
