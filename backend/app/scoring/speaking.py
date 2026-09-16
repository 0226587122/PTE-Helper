"""Scoring for the speaking tasks.

The browser sends a speech-to-text transcript (when the browser supports it) and, optionally, the student's own
rating of fluency and pronunciation. Recordings never leave the browser, so the server works from text only:

* content comes from the transcript, or from the self rating when there is no transcript
* fluency and pronunciation come from the self rating when given; otherwise they are estimated from how much of
  the expected response the recogniser picked up (clear, steady speech is recognised more completely)
"""

from typing import Any

from app.scoring.result import ScoreResult
from app.scoring.text import contains_phrase, key_point_hits, lcs_length, word_count, words

CONTENT_WEIGHT = 0.4
FLUENCY_WEIGHT = 0.3
PRONUNCIATION_WEIGHT = 0.3

# Roughly how many words a complete answer contains, used to estimate delivery when there is no self rating.
TARGET_WORDS = {"DI": 50, "RL": 60, "SGD": 120, "RTS": 50}


def _rating(response: dict[str, Any], key: str) -> float | None:
    rating = (response.get("self_rating") or {}).get(key)
    if rating is None:
        return None
    return max(0.0, min(5.0, float(rating))) / 5


def _combine(content: float, response: dict[str, Any], coverage: float, detail: dict[str, Any]) -> ScoreResult:
    fluency = _rating(response, "fluency")
    pronunciation = _rating(response, "pronunciation")
    detail["delivery_source"] = "self_rating" if fluency is not None or pronunciation is not None else "transcript"
    fluency = coverage if fluency is None else fluency
    pronunciation = coverage if pronunciation is None else pronunciation
    traits = {
        "content": round(content * 100),
        "fluency": round(fluency * 100),
        "pronunciation": round(pronunciation * 100),
    }
    detail["traits"] = traits
    total = CONTENT_WEIGHT * content + FLUENCY_WEIGHT * fluency + PRONUNCIATION_WEIGHT * pronunciation
    return ScoreResult(score=round(total * 100, 1), max_score=100, detail=detail)


def _no_answer(response: dict[str, Any]) -> bool:
    return not words(response.get("transcript")) and _rating(response, "content") is None


def _zero(detail: dict[str, Any] | None = None) -> ScoreResult:
    return ScoreResult(
        score=0, max_score=100, detail=detail or {},
        zeroed_reason="We didn't pick up an answer. Check your microphone, or use the self rating after you speak.",
    )


def score_read_aloud(text: str, response: dict[str, Any]) -> ScoreResult:
    if _no_answer(response):
        return _zero()
    expected = words(text)
    spoken = words(response.get("transcript"))
    if spoken:
        matched = lcs_length(expected, spoken)
        content = matched / len(expected)
        detail = {"words_matched": matched, "words_total": len(expected)}
    else:
        content = _rating(response, "content") or 0.0
        detail = {"content_source": "self_rating"}
    return _combine(content, response, content, detail)


def score_repeat_sentence(sentence: str, response: dict[str, Any]) -> ScoreResult:
    """Content uses the PTE bands: 3 for every word in order, 2 for at least half, 1 for fewer, 0 for nothing."""
    if _no_answer(response):
        return _zero()
    expected = words(sentence)
    spoken = words(response.get("transcript"))
    if spoken:
        matched = lcs_length(expected, spoken)
        ratio = matched / len(expected)
        band = 3 if matched == len(expected) else 2 if ratio >= 0.5 else 1 if matched > 0 else 0
        detail = {"words_matched": matched, "words_total": len(expected), "content_band": band}
        return _combine(band / 3, response, ratio, detail)
    content = _rating(response, "content") or 0.0
    return _combine(content, response, content, {"content_source": "self_rating"})


def _open_response(code: str, key_points: list[str], response: dict[str, Any], min_words: int) -> ScoreResult:
    """Describe Image, Retell Lecture, Summarize Group Discussion and Respond to a Situation."""
    if _no_answer(response):
        return _zero()
    transcript = response.get("transcript")
    count = word_count(transcript)
    if count:
        if count < min_words:
            return ScoreResult(
                score=0, max_score=100, detail={"word_count": count},
                zeroed_reason=f"Your answer was very short ({count} words). Try to keep talking for most of the time.",
            )
        hits = key_point_hits(transcript, key_points)
        content = sum(hits) / len(hits) if hits else 0.0
        coverage = min(1.0, count / TARGET_WORDS[code])
        detail = {"word_count": count, "key_points_covered": hits}
        return _combine(content, response, coverage, detail)
    content = _rating(response, "content") or 0.0
    return _combine(content, response, content, {"content_source": "self_rating"})


def score_describe_image(key_points: list[str], response: dict[str, Any]) -> ScoreResult:
    return _open_response("DI", key_points, response, min_words=10)


def score_retell_lecture(key_points: list[str], response: dict[str, Any]) -> ScoreResult:
    return _open_response("RL", key_points, response, min_words=10)


def score_group_discussion(key_points: list[str], response: dict[str, Any]) -> ScoreResult:
    return _open_response("SGD", key_points, response, min_words=20)


def score_respond_to_situation(key_points: list[str], response: dict[str, Any]) -> ScoreResult:
    return _open_response("RTS", key_points, response, min_words=10)


def score_short_answer(accepted: list[str], response: dict[str, Any]) -> ScoreResult:
    """Answer Short Question: one mark if any accepted answer appears in what was said."""
    spoken = words(response.get("transcript"))
    if not spoken:
        said_correct = bool((response.get("self_rating") or {}).get("correct"))
        return ScoreResult(score=1 if said_correct else 0, max_score=1, detail={"content_source": "self_rating"})
    ok = any(contains_phrase(spoken, words(answer)) for answer in accepted)
    return ScoreResult(score=1 if ok else 0, max_score=1, detail={"correct": ok})
