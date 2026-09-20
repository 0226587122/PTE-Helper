"""The word list a student's typing is checked against.

Three layers, all offline so scoring never depends on a network call:

1. The bundled American English list from pyspellchecker (about 160,000 words).
2. British and Australian forms generated from it, because PTE accepts all three (see variants.py).
3. An allowlist taken from the question bank itself: the words of the passage, lecture or sentence a
   student is answering. A student who correctly types a proper noun or a technical term out of the
   source text must never be told they misspelled it.
"""

from functools import lru_cache

from app.spelling.variants import expand

# Words that are correct in an answer but are not ordinary dictionary words.
EXTRA = frozenset("ok okay email online website internet smartphone smartphones dataset datasets".split())


@lru_cache(maxsize=1)
def _base() -> frozenset[str]:
    """The American list plus its British and Australian forms. Built once, then cached."""
    from spellchecker import SpellChecker

    american = set(SpellChecker(language="en").word_frequency.dictionary.keys())
    return frozenset(american | expand(american) | EXTRA)


def known(word: str) -> bool:
    """Is this a word in any of the three accepted spellings?"""
    return word.lower() in _base()


def size() -> int:
    return len(_base())


def allowlist(*texts: str | None) -> frozenset[str]:
    """Every word appearing in the source material for a question, which is correct by definition."""
    from app.scoring.text import words

    out: set[str] = set()
    for text in texts:
        out.update(words(text))
    return frozenset(out)
