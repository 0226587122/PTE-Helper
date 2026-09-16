"""Reading question bank JSON files.

Every bank file has the same shape::

    {
      "version": 1,
      "notes": "...",
      "sources": [{"source_key", "kind", "title", "body", "blank_markup"?, "turns"?}],
      "questions": [{"type", "source_key"?, "status", "difficulty"?, "payload": {...}}]
    }
"""

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BANK_PATHS = [
    REPO_ROOT / "reference" / "pte_seed_questions.json",
    REPO_ROOT / "seed" / "generated",
]


def bank_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files += sorted(path.glob("*.json"))
        elif path.is_file():
            files.append(path)
    return files


def load_bank(paths: list[Path] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[Path]]:
    files = bank_files(paths or DEFAULT_BANK_PATHS)
    sources: list[dict[str, Any]] = []
    questions: list[dict[str, Any]] = []
    for file in files:
        data = json.loads(file.read_text(encoding="utf-8"))
        sources += data.get("sources", [])
        questions += data.get("questions", [])
    return sources, questions, files
