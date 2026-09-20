"""Scoring for Summarize Written Text, Write Essay and Summarize Spoken Text.

Form is checked first, exactly as in the real test: if the form score is zero, the whole response scores zero.
The other traits use simple, transparent checks. Claude's examiner feedback gives a fuller view on top of this.
"""

import re

from app.scoring import spelling
from app.scoring.result import ScoreResult
from app.scoring.text import key_point_hits, sentences, type_token_ratio, word_count

LINKING_WORDS = (
    "however", "therefore", "moreover", "furthermore", "although", "whereas", "consequently", "in addition",
    "for example", "for instance", "in conclusion", "on the other hand", "as a result", "nevertheless", "similarly",
    "in contrast", "firstly", "secondly", "finally", "overall",
)


def _band(value: float, top: float, middle: float) -> int:
    return 2 if value >= top else 1 if value >= middle else 0


def _content_points(text: str, key_points: list[str], max_points: int) -> tuple[int, list[bool]]:
    hits = key_point_hits(text, key_points)
    if not hits:
        return 0, hits
    return round(max_points * sum(hits) / len(hits)), hits


def _grammar(text: str) -> int:
    parts = sentences(text)
    if not parts:
        return 0
    well_formed = sum(1 for s in parts if s[0].isupper() and s.rstrip()[-1] in ".!?")
    return _band(well_formed / len(parts), 0.9, 0.5)


def _vocabulary(text: str, top: float, middle: float) -> int:
    return _band(type_token_ratio(text), top, middle)


def _spelling(text: str, *context: str | None) -> tuple[int, dict]:
    """The Spelling trait, plus the detail the report lists the misspelled words from."""
    result = spelling.check(text, *context)
    return spelling.trait(result.errors_per_hundred), spelling.spelling_detail(result)


def score_summarize_written_text(text: str | None, key_points: list[str]) -> ScoreResult:
    text = text or ""
    count = word_count(text)
    parts = sentences(text)
    one_sentence = len(parts) == 1
    detail: dict = {"word_count": count, "sentence_count": len(parts)}
    if not (5 <= count <= 75) or not one_sentence:
        reason = "Your summary must be one sentence of 5 to 75 words."
        detail["traits"] = {"form": 0}
        return ScoreResult(score=0, max_score=9, detail=detail, zeroed_reason=reason)
    content, hits = _content_points(text, key_points, 2)
    spelling_score, spelling_detail = _spelling(text, *key_points)
    traits = {
        "form": 1,
        "content": content,
        "grammar": 2 if text[0].isupper() and text.rstrip().endswith(".") else 1,
        "vocabulary": _vocabulary(text, 0.7, 0.5),
        "spelling": spelling_score,
    }
    detail.update(traits=traits, key_points_covered=hits, spelling=spelling_detail)
    return ScoreResult(score=sum(traits.values()), max_score=9, detail=detail)


def _essay_form(count: int) -> int:
    if 200 <= count <= 300:
        return 2
    if 120 <= count <= 199 or 301 <= count <= 380:
        return 1
    return 0


def score_write_essay(text: str | None, key_points: list[str]) -> ScoreResult:
    text = text or ""
    count = word_count(text)
    form = _essay_form(count)
    detail: dict = {"word_count": count}
    if form == 0:
        detail["traits"] = {"form": 0}
        return ScoreResult(
            score=0, max_score=15, detail=detail,
            zeroed_reason="Essays under 120 words or over 380 words score zero. Aim for 200 to 300 words.",
        )
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    lowered = text.lower()
    linking = sum(1 for w in LINKING_WORDS if re.search(rf"\b{re.escape(w)}\b", lowered))
    content, hits = _content_points(text, key_points, 3)
    spelling_score, spelling_detail = _spelling(text, *key_points)
    traits = {
        "form": form,
        "content": content,
        "structure": 2 if len(paragraphs) >= 3 else 1 if len(paragraphs) == 2 else 0,
        "grammar": _grammar(text),
        "linguistic_range": 2 if linking >= 4 else 1 if linking >= 2 else 0,
        "vocabulary": _vocabulary(text, 0.6, 0.45),
        "spelling": spelling_score,
    }
    detail.update(
        traits=traits, key_points_covered=hits, paragraphs=len(paragraphs), linking_words=linking,
        spelling=spelling_detail,
    )
    return ScoreResult(score=sum(traits.values()), max_score=15, detail=detail)


def _summary_form(count: int) -> int:
    if 50 <= count <= 70:
        return 2
    if 40 <= count <= 49 or 71 <= count <= 100:
        return 1
    return 0


def score_summarize_spoken_text(text: str | None, key_points: list[str]) -> ScoreResult:
    text = text or ""
    count = word_count(text)
    form = _summary_form(count)
    detail: dict = {"word_count": count}
    if form == 0:
        detail["traits"] = {"form": 0}
        return ScoreResult(
            score=0, max_score=10, detail=detail,
            zeroed_reason="Summaries under 40 words or over 100 words score zero. Aim for 50 to 70 words.",
        )
    content, hits = _content_points(text, key_points, 2)
    spelling_score, spelling_detail = _spelling(text, *key_points)
    traits = {
        "form": form,
        "content": content,
        "grammar": _grammar(text),
        "vocabulary": _vocabulary(text, 0.65, 0.5),
        "spelling": spelling_score,
    }
    detail.update(traits=traits, key_points_covered=hits, spelling=spelling_detail)
    return ScoreResult(score=sum(traits.values()), max_score=10, detail=detail)
