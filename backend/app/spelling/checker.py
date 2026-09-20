"""Finding misspelled words, and telling a near miss from a different word.

Two questions get asked of this module, and they are not the same question:

* "Is this a word?" - for the Spelling enabling skill, over everything a student typed.
* "Is this a misspelling of *that* word?" - for Write from Dictation and the listening blanks, where
  the answer key says exactly which word was expected. "definately" for "definitely" is a spelling
  mistake; "however" for "definitely" is the wrong word, and is not a spelling mistake at all.

Edit distance decides the second question: one or two edits from the expected word, and the student
clearly heard it and mistyped it. Three or more, and there is no evidence they heard it.
"""

from dataclasses import dataclass, field

from app.spelling.dictionary import allowlist, known

# How far a typed word can sit from the expected one and still count as that word, misspelled.
NEAR_MISS_MAX_EDITS = 2

# Short words allow one edit only. Two edits on a four-letter word leaves almost nothing of the
# original, so "cost" is not treated as an attempt at "cat".
SHORT_WORD_LENGTH = 5


def edit_distance(a: str, b: str, cap: int = NEAR_MISS_MAX_EDITS) -> int:
    """Levenshtein distance, stopping early once it exceeds the cap."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, start=1):
        current = [i]
        for j, y in enumerate(b, start=1):
            current.append(
                previous[j - 1] if x == y else 1 + min(previous[j - 1], previous[j], current[j - 1])
            )
        if min(current) > cap:
            return cap + 1
        previous = current
    return previous[-1]


def near_miss(typed: str, expected: str) -> bool:
    """Is `typed` a misspelling of `expected`, rather than a different word?"""
    if typed == expected:
        return False
    allowed = 1 if min(len(typed), len(expected)) < SHORT_WORD_LENGTH else NEAR_MISS_MAX_EDITS
    return edit_distance(typed, expected, allowed) <= allowed


def intended_word(typed: str, candidates: frozenset[str] | set[str]) -> str | None:
    """The word a misspelling was most likely meant to be, or None if nothing is close enough."""
    best: tuple[int, str] | None = None
    for candidate in candidates:
        if not near_miss(typed, candidate):
            continue
        distance = edit_distance(typed, candidate)
        if best is None or distance < best[0] or (distance == best[0] and candidate < best[1]):
            best = (distance, candidate)
    return best[1] if best else None


@dataclass(frozen=True)
class SpellingCheck:
    """What a piece of typed text looks like, spelling-wise."""

    typed_words: int
    misspellings: list[dict[str, str | None]] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.misspellings)

    @property
    def errors_per_hundred(self) -> float | None:
        """Errors per 100 typed words. None when nothing was typed."""
        if not self.typed_words:
            return None
        return round(self.error_count / self.typed_words * 100, 1)


def check(text: str | None, *context: str | None) -> SpellingCheck:
    """Check everything a student typed, treating the question's own source text as correct.

    Each distinct misspelling is reported once, with the word it was probably meant to be, so a
    student can see what to learn rather than a count.
    """
    from app.scoring.text import words  # imported here: app.scoring imports this module

    typed = words(text)
    if not typed:
        return SpellingCheck(typed_words=0)

    context_words = allowlist(*context)
    misspellings: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for word in typed:
        if word in seen or word.isdigit() or known(word) or word in context_words:
            continue
        # A word out of the passage the student is answering is correct whatever the dictionary says.
        seen.add(word)
        misspellings.append({"typed": word, "intended": _suggest(word, context_words)})
    return SpellingCheck(typed_words=len(typed), misspellings=misspellings)


def _suggest(word: str, context_words: frozenset[str]) -> str | None:
    """The intended word: something from the question's own text first, then the dictionary."""
    from_context = intended_word(word, context_words)
    if from_context:
        return from_context

    correction = _speller().correction(word)
    return correction if correction and correction != word and near_miss(word, correction) else None


def _speller():
    global _SPELLER
    if _SPELLER is None:
        from spellchecker import SpellChecker

        _SPELLER = SpellChecker(language="en", distance=NEAR_MISS_MAX_EDITS)
    return _SPELLER


_SPELLER = None
