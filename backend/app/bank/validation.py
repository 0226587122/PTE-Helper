"""Checks for question bank content. Used by the validator script, the seed script and admin edits."""

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.bank import markup
from app.models import QUESTION_STATUSES, SOURCE_KINDS
from app.scoring.text import normalise_answer, word_count, words
from app.task_types import TYPES, TYPES_BY_CODE

WORD_LIMITS = {
    "lecture": (110, 150),
    "passage": (90, 130),
}


def content_hash(code: str, source_key: str | None, payload: dict[str, Any]) -> str:
    canonical = json.dumps({"type": code, "source_key": source_key, "payload": payload}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _text_list(payload: dict[str, Any], key: str, lo: int, hi: int, errors: list[str]) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(_is_text(v) for v in value):
        errors.append(f"'{key}' must be a list of non-empty strings.")
        return []
    if not lo <= len(value) <= hi:
        errors.append(f"'{key}' must have {lo} to {hi} items (found {len(value)}).")
    if len({normalise_answer(v) for v in value}) != len(value):
        errors.append(f"'{key}' has duplicate items.")
    return value


def _index(payload: dict[str, Any], key: str, size: int, errors: list[str]) -> None:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < size:
        errors.append(f"'{key}' must be an option index from 0 to {size - 1}.")


def _word_range(label: str, text: str, lo: int, hi: int, errors: list[str]) -> None:
    count = word_count(text)
    if not lo <= count <= hi:
        errors.append(f"{label} should be {lo} to {hi} words (found {count}).")


def validate_source(source: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("source_key", "kind", "title", "body"):
        if not _is_text(source.get(key)):
            errors.append(f"'{key}' is required.")
    if errors:
        return errors
    kind = source["kind"]
    if kind not in SOURCE_KINDS:
        return [f"Unknown kind '{kind}'."]
    if kind in WORD_LIMITS:
        _word_range(f"A {kind}", source["body"], *WORD_LIMITS[kind], errors)
    if kind == "passage":
        if not _is_text(source.get("blank_markup")):
            errors.append("Passages need 'blank_markup'.")
        else:
            try:
                _, blanks = markup.parse(source["blank_markup"])
            except markup.MarkupError as exc:
                errors.append(f"Blank markup does not parse: {exc}")
            else:
                if not 4 <= len(blanks) <= 5:
                    errors.append(f"Passages need 4 or 5 blanks (found {len(blanks)}).")
                if any(len(b.distractors) < 3 for b in blanks):
                    errors.append("Every blank needs at least 3 distractors.")
                if markup.fill(source["blank_markup"]) != source["body"]:
                    errors.append("Filling the blank markup with the correct answers must give exactly the body text.")
    if kind == "discussion":
        turns = source.get("turns")
        if not isinstance(turns, list) or len(turns) < 3:
            errors.append("Discussions need at least 3 'turns'.")
        elif not all(isinstance(t, dict) and _is_text(t.get("speaker")) and _is_text(t.get("text")) for t in turns):
            errors.append("Every turn needs 'speaker' and 'text'.")
        elif len({t["speaker"] for t in turns}) < 2:
            errors.append("Discussions need at least 2 speakers.")
        else:
            _word_range("A discussion", " ".join(t["text"] for t in turns), 110, 300, errors)
    return errors


def validate_payload(code: str, payload: Any, source: dict[str, Any] | None) -> list[str]:
    """Check one question payload. `source` is the source row as a dict (or None)."""
    errors: list[str] = []
    definition = TYPES_BY_CODE.get(code)
    if definition is None:
        return [f"Unknown task type '{code}'."]
    if not isinstance(payload, dict):
        return ["'payload' must be an object."]
    if definition.uses_source:
        if source is None:
            return [f"{code} questions need a {definition.uses_source} source."]
        if source.get("kind") != definition.uses_source:
            return [f"{code} questions need a {definition.uses_source} source, not a {source.get('kind')}."]
    elif source is not None:
        errors.append(f"{code} questions do not use a source.")
    p = payload

    if code == "RA":
        if not _is_text(p.get("text")):
            return ["'text' is required."]
        _word_range("Read Aloud text", p["text"], 35, 70, errors)
    elif code in ("RS", "WFD"):
        if not _is_text(p.get("sentence")):
            return ["'sentence' is required."]
        _word_range("The sentence", p["sentence"], 8, 16, errors)
    elif code == "DI":
        if p.get("chart") not in ("bar", "line", "pie"):
            errors.append("'chart' must be bar, line or pie.")
        if not _is_text(p.get("title")):
            errors.append("'title' is required.")
        categories = _text_list(p, "categories", 3, 8, errors)
        if p.get("chart") in ("bar", "line"):
            lo, hi = p.get("min"), p.get("max")
            if not (isinstance(lo, int) and isinstance(hi, int) and lo < hi):
                errors.append("Bar and line charts need integer 'min' below 'max'.")
            elif p.get("chart") == "bar" and hi - lo + 1 < len(categories):
                errors.append("The min to max range is too small for distinct bar values.")
    elif code in ("RL", "SST", "SGD", "SWT"):
        _text_list(p, "key_points", 3, 6, errors)
    elif code == "ASQ":
        if not _is_text(p.get("question")) or not p["question"].strip().endswith("?"):
            errors.append("'question' must be a question ending with '?'.")
        _text_list(p, "accepted", 1, 6, errors)
    elif code == "RTS":
        if not _is_text(p.get("situation")):
            errors.append("'situation' is required.")
        else:
            _word_range("The situation", p["situation"], 30, 90, errors)
        _text_list(p, "key_points", 3, 6, errors)
    elif code == "WE":
        if not _is_text(p.get("prompt")):
            errors.append("'prompt' is required.")
        _text_list(p, "key_points", 3, 6, errors)
    elif code == "RWFIB":
        pass  # everything lives in the passage's blank markup
    elif code == "RFIB":
        extra = _text_list(p, "extra_words", 2, 5, errors)
        if source and source.get("blank_markup") and extra:
            try:
                _, blanks = markup.parse(source["blank_markup"])
            except markup.MarkupError:
                blanks = []
            correct = {b.correct.lower() for b in blanks}
            if any(w.lower() in correct for w in extra):
                errors.append("'extra_words' must not repeat a correct answer.")
    elif code in ("MCMA", "LMCMA"):
        if not _is_text(p.get("question")):
            errors.append("'question' is required.")
        options = _text_list(p, "options", 5, 7, errors)
        answers = p.get("answers")
        if (
            not isinstance(answers, list)
            or len(answers) < 2
            or len(set(answers)) != len(answers)
            or not all(isinstance(a, int) and not isinstance(a, bool) and 0 <= a < len(options) for a in answers)
        ):
            errors.append("'answers' must list at least 2 different option indexes in range.")
        elif len(answers) >= len(options):
            errors.append("At least one option must be wrong.")
    elif code in ("MCSA", "LMCSA"):
        if not _is_text(p.get("question")):
            errors.append("'question' is required.")
        options = _text_list(p, "options", 4, 5, errors)
        _index(p, "answer", len(options), errors)
    elif code == "HCS":
        options = _text_list(p, "options", 3, 4, errors)
        for option in options:
            _word_range("Each summary", option, 15, 90, errors)
        _index(p, "answer", len(options), errors)
    elif code == "SMW":
        options = _text_list(p, "options", 4, 5, errors)
        _index(p, "answer", len(options), errors)
        if not errors and source:
            ending = options[p["answer"]]
            spoken = source["body"].rstrip().rstrip(".!?")
            if not spoken.lower().endswith(ending.lower()):
                errors.append("The lecture must end with the correct missing words.")
            if word_count(ending) > 6:
                errors.append("The missing words should be 6 words or fewer.")
    elif code == "HIW":
        swaps = p.get("hiw_swaps")
        if not isinstance(swaps, list) or len(swaps) < 4:
            errors.append("'hiw_swaps' needs at least 4 [original, replacement] pairs.")
        else:
            # Match the renderer exactly: whole whitespace tokens, ignoring surrounding punctuation.
            from app.variants import token_cores

            body_words = token_cores(source["body"]) if source else set()
            originals = []
            for pair in swaps:
                if not (isinstance(pair, list) and len(pair) == 2 and all(_is_text(x) for x in pair)):
                    errors.append("Each swap must be [original, replacement].")
                    continue
                original, replacement = pair
                originals.append(original.lower())
                if len(words(original)) != 1 or len(words(replacement)) != 1:
                    errors.append(f"Swap {pair} must be single words.")
                elif original.lower() == replacement.lower():
                    errors.append(f"Swap {pair} does not change the word.")
                elif source and original.lower() not in body_words:
                    errors.append(f"'{original}' does not appear in the lecture.")
            if len(set(originals)) != len(originals):
                errors.append("Each swap must change a different word.")
    elif code == "LFIB":
        if source and word_count(source["body"]) < 35:
            errors.append("The lecture is too short for Listening Fill in the Blanks.")
    elif code == "RO":
        _text_list(p, "paragraphs", 4, 5, errors)
    return errors


def duplicate_key(code: str, source_key: str | None, payload: dict[str, Any]) -> str:
    """The text that must be unique within a task type."""
    text_field = {"RA": "text", "RS": "sentence", "WFD": "sentence", "ASQ": "question", "WE": "prompt", "RTS": "situation", "DI": "title"}
    if code in text_field:
        return normalise_answer(str(payload.get(text_field[code], "")))
    if code == "RO":
        return normalise_answer(" ".join(payload.get("paragraphs", [])))
    return f"source:{source_key}"


@dataclass
class BankReport:
    errors: list[str] = field(default_factory=list)
    counts: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_bank(
    sources: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    min_active: int = 0,
    min_backup: int = 0,
) -> BankReport:
    report = BankReport()
    by_key: dict[str, dict[str, Any]] = {}
    bodies: dict[str, str] = {}
    for i, source in enumerate(sources):
        label = f"source {source.get('source_key') or f'#{i}'}"
        for error in validate_source(source):
            report.errors.append(f"{label}: {error}")
        key = source.get("source_key")
        if key in by_key:
            report.errors.append(f"{label}: duplicate source_key.")
        by_key[key] = source
        body = normalise_answer(source.get("body"))
        if body and body in bodies:
            report.errors.append(f"{label}: same text as source {bodies[body]}.")
        bodies[body] = key

    seen_text: dict[tuple[str, str], int] = {}
    seen_hash: set[str] = set()
    for i, question in enumerate(questions):
        code = question.get("type")
        source_key = question.get("source_key")
        label = f"question #{i} ({code}{', ' + source_key if source_key else ''})"
        status = question.get("status", "active")
        if status not in QUESTION_STATUSES:
            report.errors.append(f"{label}: unknown status '{status}'.")
        difficulty = question.get("difficulty")
        if difficulty is not None and difficulty not in (1, 2, 3):
            report.errors.append(f"{label}: difficulty must be 1, 2 or 3.")
        if source_key and source_key not in by_key:
            report.errors.append(f"{label}: source_key '{source_key}' does not exist.")
            continue
        source = by_key.get(source_key) if source_key else None
        payload = question.get("payload")
        for error in validate_payload(code, payload, source):
            report.errors.append(f"{label}: {error}")
        if code not in TYPES_BY_CODE or not isinstance(payload, dict):
            continue
        digest = content_hash(code, source_key, payload)
        if digest in seen_hash:
            report.errors.append(f"{label}: exact duplicate of another question.")
        seen_hash.add(digest)
        dup = (code, duplicate_key(code, source_key, payload))
        if dup in seen_text:
            report.errors.append(f"{label}: same text as question #{seen_text[dup]}.")
        seen_text[dup] = i
        report.counts[code][status] += 1

    for definition in TYPES:
        counts = report.counts[definition.code]
        if counts["active"] < min_active:
            report.errors.append(f"{definition.code}: only {counts['active']} active questions (need {min_active}).")
        if counts["backup"] < min_backup:
            report.errors.append(f"{definition.code}: only {counts['backup']} backup questions (need {min_backup}).")
    return report
