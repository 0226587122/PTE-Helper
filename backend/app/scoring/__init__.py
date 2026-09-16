"""Server-side scoring. The score calculated here is the one that counts.

Response shapes sent by the browser:

* speaking (RA, RS, DI, RL, ASQ, SGD, RTS): ``{"transcript": str, "self_rating": {...}}``
* typed text (SWT, WE, SST, WFD): ``{"text": str}``
* blanks (RWFIB, RFIB, LFIB): ``{"answers": [str | None, ...]}``
* several choices (MCMA, LMCMA) and clicked words (HIW): ``{"selected": [int, ...]}``
* one choice (MCSA, LMCSA, HCS, SMW): ``{"selected": int}``
* reorder (RO): ``{"order": ["B", "A", ...]}``
"""

from typing import Any

from app.scoring import objective, speaking, writing
from app.scoring.result import ScoreResult, estimated_score

__all__ = ["ScoreResult", "estimated_score", "score_answer"]


def _int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, int) and not isinstance(v, bool)]


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def score_answer(code: str, rendered: dict[str, Any], response: dict[str, Any]) -> ScoreResult:
    answer = rendered["answer"]
    response = response or {}

    if code == "RA":
        return speaking.score_read_aloud(answer["text"], response)
    if code == "RS":
        return speaking.score_repeat_sentence(answer["sentence"], response)
    if code == "DI":
        return speaking.score_describe_image(answer["key_points"], response)
    if code == "RL":
        return speaking.score_retell_lecture(answer["key_points"], response)
    if code == "ASQ":
        return speaking.score_short_answer(answer["accepted"], response)
    if code == "SGD":
        return speaking.score_group_discussion(answer["key_points"], response)
    if code == "RTS":
        return speaking.score_respond_to_situation(answer["key_points"], response)

    text = response.get("text") if isinstance(response.get("text"), str) else None
    if code == "SWT":
        return writing.score_summarize_written_text(text, answer["key_points"])
    if code == "WE":
        return writing.score_write_essay(text, answer["key_points"])
    if code == "SST":
        return writing.score_summarize_spoken_text(text, answer["key_points"])
    if code == "WFD":
        return objective.score_dictation(answer["sentence"], text)

    if code in ("RWFIB", "RFIB", "LFIB"):
        given = response.get("answers")
        given = [g if isinstance(g, str) else None for g in given] if isinstance(given, list) else []
        return objective.score_blanks(answer["blanks"], given)
    if code in ("MCMA", "LMCMA"):
        return objective.score_multiple_answers(answer["correct"], _int_list(response.get("selected")))
    if code in ("MCSA", "LMCSA", "HCS", "SMW"):
        return objective.score_single_answer(answer["correct"], _int_or_none(response.get("selected")))
    if code == "RO":
        order = response.get("order")
        order = [o for o in order if isinstance(o, str)] if isinstance(order, list) else []
        return objective.score_reorder(answer["order"], order)
    if code == "HIW":
        return objective.score_incorrect_words(answer["incorrect"], _int_list(response.get("selected")))
    raise ValueError(f"Unknown task type {code}")
