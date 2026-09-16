"""Text helpers shared by the scoring rules."""

import re
from collections import Counter

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?")

STOPWORDS = frozenset(
    """
    a about above after again against all am an and any are as at be because been before being below between both
    but by can could did do does doing down during each few for from further had has have having he her here hers
    him his how i if in into is it its itself just me more most my no nor not now of off on once only or other our
    out over own same she should so some such than that the their them then there these they this those through to
    too under until up very was we were what when where which while who whom why will with would you your also
    may might must shall one two many much us
    """.split()
)


def words(text: str | None) -> list[str]:
    """Lower-case word tokens with punctuation removed."""
    if not text:
        return []
    return [w.lower().replace("’", "'") for w in _WORD_RE.findall(text)]


def word_count(text: str | None) -> int:
    return len(words(text))


def normalise_answer(text: str | None) -> str:
    return " ".join(words(text))


def stem(word: str) -> str:
    """A deliberately rough stem: enough to match 'economy' with 'economic' or 'rising' with 'rise'."""
    return word[:5] if len(word) > 5 else word


def content_words(text: str | None) -> list[str]:
    return [w for w in words(text) if w not in STOPWORDS and len(w) > 2]


def lcs_length(a: list[str], b: list[str]) -> int:
    """Longest common subsequence of two word lists (words in the right order)."""
    if not a or not b:
        return 0
    previous = [0] * (len(b) + 1)
    for x in a:
        current = [0]
        for j, y in enumerate(b, start=1):
            current.append(previous[j - 1] + 1 if x == y else max(previous[j], current[j - 1]))
        previous = current
    return previous[-1]


def multiset_matches(expected: list[str], given: list[str]) -> int:
    """How many expected words appear in the answer, counting repeated words only as often as they occur."""
    remaining = Counter(given)
    hits = 0
    for w in expected:
        if remaining[w] > 0:
            remaining[w] -= 1
            hits += 1
    return hits


def contains_phrase(haystack: list[str], phrase: list[str]) -> bool:
    if not phrase:
        return False
    n = len(phrase)
    return any(haystack[i : i + n] == phrase for i in range(len(haystack) - n + 1))


def key_point_hits(text: str | None, key_points: list[str]) -> list[bool]:
    """A key point counts as covered when at least half of its content words (by rough stem) appear in the text."""
    available = {stem(w) for w in content_words(text)}
    hits = []
    for point in key_points:
        point_words = {stem(w) for w in content_words(point)}
        if not point_words:
            hits.append(False)
            continue
        hits.append(len(point_words & available) / len(point_words) >= 0.5)
    return hits


def sentences(text: str | None) -> list[str]:
    if not text or not text.strip():
        return []
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if words(p)]


def type_token_ratio(text: str | None) -> float:
    cw = content_words(text)
    return len(set(cw)) / len(cw) if cw else 0.0
