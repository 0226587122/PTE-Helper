"""Turn a stored question into the exact variant a student sees.

Every rendered question has two parts:

* ``display``: everything the browser needs to show and play the question. Safe to send before answering.
* ``answer``: the answer key and any review material. Only sent after the student answers.

Some types are generated here with a per-question random seed (Describe Image charts, Listening Fill in the
Blanks, Highlight Incorrect Words), and option order is shuffled for choice tasks. The result is stored on the
set question so scoring and review always match what the student saw.
"""

import random
import re
from dataclasses import dataclass
from typing import Any

from app.bank import markup
from app.scoring.text import STOPWORDS

_CORE_RE = re.compile(r"^([^A-Za-z0-9']*)([A-Za-z0-9'’-]+)([^A-Za-z0-9']*)$")


@dataclass
class SourceData:
    source_key: str
    kind: str
    title: str
    body: str
    blank_markup: str | None = None
    turns: list[dict[str, Any]] | None = None


def _shuffled_options(rng: random.Random, options: list[str]) -> tuple[list[str], list[int]]:
    """Shuffle options; returns the new list and, for each new position, the original index."""
    order = list(range(len(options)))
    rng.shuffle(order)
    return [options[i] for i in order], order


def _split_token(token: str) -> tuple[str, str, str] | None:
    match = _CORE_RE.match(token)
    return (match.group(1), match.group(2), match.group(3)) if match else None


def _match_case(template: str, word: str) -> str:
    return word[:1].upper() + word[1:] if template[:1].isupper() else word


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


# ---------- generated types ----------


def render_describe_image(payload: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    kind = payload["chart"]
    categories = list(payload["categories"])
    low, high = payload.get("min", 0), payload.get("max", 100)
    if kind == "pie":
        weights = [rng.uniform(1, 4) for _ in categories]
        total = sum(weights)
        values = [round(100 * w / total) for w in weights]
        values[values.index(max(values))] += 100 - sum(values)
    elif kind == "line":
        values = [rng.randint(low, high)]
        step = max(1, (high - low) // 4)
        direction = rng.choice([1, -1])
        for _ in categories[1:]:
            nxt = values[-1] + direction * rng.randint(0, step) + rng.randint(-step // 3, step // 3)
            values.append(max(low, min(high, nxt)))
        if values[-1] == values[0]:
            values[-1] = max(low, min(high, values[-1] + direction * step)) if low < high else values[-1]
    else:
        values = rng.sample(range(low, high + 1), len(categories)) if high - low + 1 >= len(categories) else [
            rng.randint(low, high) for _ in categories
        ]
    top = categories[values.index(max(values))]
    bottom = categories[values.index(min(values))]
    key_points = [payload["title"], f"{top} highest", f"{bottom} lowest"]
    if kind == "line":
        change = "increased" if values[-1] > values[0] else "decreased"
        key_points.append(f"{change} from {categories[0]} to {categories[-1]}")
    unit = payload.get("unit", "")
    chart = {
        "kind": kind,
        "title": payload["title"],
        "unit": unit,
        "x_label": payload.get("x_label"),
        "y_label": payload.get("y_label"),
        "categories": categories,
        "values": values,
    }
    return {
        "display": {"chart": chart},
        "answer": {
            "key_points": key_points,
            "notes": f"Highest: {top} ({values[categories.index(top)]}{unit}). "
            f"Lowest: {bottom} ({values[categories.index(bottom)]}{unit}).",
        },
    }


def render_listening_blanks(source: SourceData, payload: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    sentences = _sentences(source.body)
    min_words = payload.get("min_words", 35)
    starts = list(range(len(sentences)))
    rng.shuffle(starts)
    snippet_sentences = sentences
    for start in starts:
        chosen: list[str] = []
        for sentence in sentences[start:]:
            chosen.append(sentence)
            if len(" ".join(chosen).split()) >= min_words:
                break
        if len(" ".join(chosen).split()) >= min_words:
            snippet_sentences = chosen
            break
    snippet = " ".join(snippet_sentences)
    tokens = snippet.split()
    candidates = []
    for i, token in enumerate(tokens):
        parts = _split_token(token)
        if parts and parts[1].isalpha() and len(parts[1]) >= 4 and parts[1].lower() not in STOPWORDS:
            candidates.append(i)
    wanted = min(len(candidates), rng.randint(payload.get("min_blanks", 4), payload.get("max_blanks", 6)))
    picked: list[int] = []
    for i in rng.sample(candidates, len(candidates)):
        if len(picked) == wanted:
            break
        if all(abs(i - j) > 1 for j in picked):
            picked.append(i)
    picked.sort()
    segments: list[Any] = []
    blanks: list[str] = []
    text = ""
    for i, token in enumerate(tokens):
        separator = " " if i else ""
        if i in picked:
            lead, core, trail = _split_token(token)  # type: ignore[misc]
            text += separator + lead
            if text:
                segments.append(text)
            segments.append({"blank": len(blanks)})
            blanks.append(core)
            text = trail
        else:
            text += separator + token
    if text:
        segments.append(text)
    return {
        "display": {"audio": snippet, "segments": segments},
        "answer": {"blanks": blanks, "transcript": snippet},
    }


def render_incorrect_words(source: SourceData, payload: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    tokens = source.body.split()
    swaps = [tuple(s) for s in payload["hiw_swaps"]]
    count = rng.randint(min(3, len(swaps)), min(5, len(swaps)))
    chosen = rng.sample(swaps, count)
    changed: dict[int, str] = {}
    for original, replacement in chosen:
        for i, token in enumerate(tokens):
            parts = _split_token(token)
            if i in changed or not parts or parts[1].lower() != original.lower():
                continue
            lead, core, trail = parts
            tokens[i] = f"{lead}{_match_case(core, replacement)}{trail}"
            changed[i] = core
            break
    indexes = sorted(changed)
    return {
        "display": {"audio": source.body, "tokens": tokens},
        "answer": {"incorrect": indexes, "originals": {str(i): changed[i] for i in indexes}, "transcript": source.body},
    }


# ---------- all types ----------


def render(code: str, payload: dict[str, Any], source: SourceData | None, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    p = payload

    if code == "RA":
        return {"display": {"text": p["text"]}, "answer": {"text": p["text"]}}
    if code in ("RS", "WFD"):
        return {"display": {"audio": p["sentence"]}, "answer": {"sentence": p["sentence"]}}
    if code == "DI":
        return render_describe_image(p, rng)
    if code in ("RL", "SST"):
        assert source
        return {
            "display": {"audio": source.body},
            "answer": {"key_points": p["key_points"], "transcript": source.body},
        }
    if code == "ASQ":
        return {"display": {"audio": p["question"]}, "answer": {"accepted": p["accepted"], "transcript": p["question"]}}
    if code == "SGD":
        assert source and source.turns
        return {
            "display": {"turns": source.turns},
            "answer": {"key_points": p["key_points"], "transcript": source.turns},
        }
    if code == "RTS":
        return {"display": {"situation": p["situation"], "audio": p["situation"]}, "answer": {"key_points": p["key_points"]}}
    if code == "SWT":
        assert source
        return {"display": {"passage": source.body}, "answer": {"key_points": p["key_points"]}}
    if code == "WE":
        return {"display": {"prompt": p["prompt"]}, "answer": {"key_points": p["key_points"]}}
    if code in ("RWFIB", "RFIB"):
        assert source and source.blank_markup
        pieces, blanks = markup.parse(source.blank_markup)
        segments: list[Any] = []
        for piece in pieces:
            if isinstance(piece, int):
                blank: dict[str, Any] = {"blank": piece}
                if code == "RWFIB":
                    blank["options"], _ = _shuffled_options(rng, [blanks[piece].correct, *blanks[piece].distractors])
                segments.append(blank)
            else:
                segments.append(piece)
        display: dict[str, Any] = {"segments": segments}
        if code == "RFIB":
            bank = [b.correct for b in blanks] + list(p.get("extra_words", []))
            rng.shuffle(bank)
            display["bank"] = bank
        return {"display": display, "answer": {"blanks": [b.correct for b in blanks], "passage": source.body}}
    if code in ("MCMA", "MCSA"):
        assert source
        options, order = _shuffled_options(rng, p["options"])
        display = {"passage": source.body, "question": p["question"], "options": options}
        if code == "MCMA":
            correct: Any = sorted(order.index(i) for i in p["answers"])
        else:
            correct = order.index(p["answer"])
        return {"display": display, "answer": {"correct": correct}}
    if code == "RO":
        labels = [chr(ord("A") + i) for i in range(len(p["paragraphs"]))]
        items = [{"id": labels[i], "text": text} for i, text in enumerate(p["paragraphs"])]
        shuffled = items[:]
        for _ in range(10):
            rng.shuffle(shuffled)
            if [x["id"] for x in shuffled] != labels:
                break
        return {"display": {"paragraphs": shuffled}, "answer": {"order": labels, "paragraphs": items}}
    if code in ("LMCMA", "LMCSA"):
        assert source
        options, order = _shuffled_options(rng, p["options"])
        display = {"audio": source.body, "question": p["question"], "options": options}
        if code == "LMCMA":
            correct = sorted(order.index(i) for i in p["answers"])
        else:
            correct = order.index(p["answer"])
        return {"display": display, "answer": {"correct": correct, "transcript": source.body}}
    if code == "HCS":
        assert source
        options, order = _shuffled_options(rng, p["options"])
        return {
            "display": {"audio": source.body, "options": options},
            "answer": {"correct": order.index(p["answer"]), "transcript": source.body},
        }
    if code == "SMW":
        assert source
        ending = p["options"][p["answer"]]
        spoken = source.body.rstrip().rstrip(".!?")
        trimmed = spoken[: len(spoken) - len(ending)].rstrip()
        options, order = _shuffled_options(rng, p["options"])
        return {
            "display": {"audio": trimmed, "options": options},
            "answer": {"correct": order.index(p["answer"]), "transcript": source.body},
        }
    if code == "LFIB":
        assert source
        return render_listening_blanks(source, p, rng)
    if code == "HIW":
        assert source
        return render_incorrect_words(source, p, rng)
    raise ValueError(f"Unknown task type {code}")
