"""Scoring for the tasks with a fixed answer key."""

from app.scoring import spelling
from app.scoring.result import ScoreResult
from app.scoring.text import multiset_matches, normalise_answer, words


def score_blanks(correct: list[str], given: list[str | None] | None, typed: bool = False) -> ScoreResult:
    """One point per blank filled correctly (Reading & Writing FIB, Reading FIB, Listening FIB)."""
    given = list(given or [])
    given += [None] * (len(correct) - len(given))
    per_blank = [normalise_answer(g) == normalise_answer(c) and bool(normalise_answer(g)) for c, g in zip(correct, given)]
    detail: dict = {"per_blank": per_blank}
    if typed:
        # Listening blanks are typed, so a wrong blank may be the right word misspelled. It still
        # scores zero, exactly as in the real test; recording it only lets the report say why.
        detail["spelling"] = spelling.spelling_detail(_typed_blanks(correct, given, per_blank))
    return ScoreResult(score=sum(per_blank), max_score=len(correct), detail=detail)


def _typed_blanks(correct: list[str], given: list[str | None], per_blank: list[bool]) -> spelling.SpellingCheck:
    """Blanks the student typed, with the near misses of the expected word marked as misspellings."""
    misspellings: list[dict[str, str | None]] = []
    typed_words = 0
    for expected, answer, right in zip(correct, given, per_blank):
        got = normalise_answer(answer)
        if not got:
            continue
        typed_words += len(words(got))
        if right:
            continue
        if spelling.near_miss(got, normalise_answer(expected)):
            misspellings.append({"typed": got, "intended": normalise_answer(expected)})
    return spelling.SpellingCheck(typed_words=typed_words, misspellings=misspellings)


def score_multiple_answers(correct: list[int], selected: list[int] | None) -> ScoreResult:
    """Plus one for each correct option chosen, minus one for each wrong option, never below zero."""
    chosen = set(selected or [])
    right = len(chosen & set(correct))
    wrong = len(chosen - set(correct))
    return ScoreResult(
        score=max(0, right - wrong),
        max_score=len(correct),
        detail={"correct_selected": right, "incorrect_selected": wrong},
    )


def score_single_answer(correct: int, selected: int | None) -> ScoreResult:
    ok = selected is not None and selected == correct
    return ScoreResult(score=1 if ok else 0, max_score=1, detail={"correct": ok})


def score_reorder(correct_order: list[str], given_order: list[str] | None) -> ScoreResult:
    """One point for each pair of neighbouring paragraphs that is also next to each other in the correct order."""
    correct_pairs = {(a, b) for a, b in zip(correct_order, correct_order[1:])}
    given_order = list(given_order or [])
    given_pairs = [(a, b) for a, b in zip(given_order, given_order[1:])]
    matched = [pair for pair in given_pairs if pair in correct_pairs]
    return ScoreResult(
        score=len(matched),
        max_score=len(correct_pairs),
        detail={"correct_pairs": [list(p) for p in matched]},
    )


def score_incorrect_words(incorrect_indexes: list[int], selected: list[int] | None) -> ScoreResult:
    """Highlight Incorrect Words: plus one per changed word clicked, minus one per wrong click, never below zero."""
    chosen = set(selected or [])
    right = len(chosen & set(incorrect_indexes))
    wrong = len(chosen - set(incorrect_indexes))
    return ScoreResult(
        score=max(0, right - wrong),
        max_score=len(incorrect_indexes),
        detail={"correct_selected": right, "incorrect_selected": wrong},
    )


def score_dictation(sentence: str, typed: str | None) -> ScoreResult:
    """Write from Dictation: one point for each word of the sentence that appears in the answer, spelled correctly.

    A word the student clearly heard but mistyped scores zero, as it does in the real test. It is
    recorded as a spelling mistake rather than silently lost, so the report can show what went wrong.
    """
    expected = words(sentence)
    given = words(typed)
    hits = multiset_matches(expected, given)
    return ScoreResult(
        score=hits,
        max_score=len(expected),
        detail={
            "words_matched": hits,
            "words_total": len(expected),
            "spelling": spelling.spelling_detail(_dictation_misspellings(expected, given)),
        },
    )


def _dictation_misspellings(expected: list[str], given: list[str]) -> spelling.SpellingCheck:
    """Typed words that are one or two edits from a word of the sentence that went unmatched."""
    missing = list(expected)
    for word in given:  # take the words that matched out of play first
        if word in missing:
            missing.remove(word)
    unmatched = [w for w in given if w not in expected]

    misspellings: list[dict[str, str | None]] = []
    for word in unmatched:
        target = spelling.intended_word(word, set(missing))
        if target:
            missing.remove(target)
            misspellings.append({"typed": word, "intended": target})
    return spelling.SpellingCheck(typed_words=len(given), misspellings=misspellings)
