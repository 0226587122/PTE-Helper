"""Load task types and the question bank into the database. Safe to run more than once.

* Task types are upserted by code.
* Sources are upserted by source_key.
* Questions are matched on a hash of their type, source and payload. Existing questions keep their status, so
  re-seeding never undoes an admin's retire or promote.

    python -m scripts.seed
    python -m scripts.seed path/to/bank.json --min-active 0 --min-backup 0
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import func, select

from app.bank.files import load_bank
from app.bank.validation import content_hash, validate_bank
from app.db import session_factory
from app.models import ContentSource, Question, TaskType
from app.task_types import TYPES


def upsert_task_types(db) -> None:
    for order, definition in enumerate(TYPES, start=1):
        row = db.get(TaskType, definition.code) or TaskType(code=definition.code)
        row.name = definition.name
        row.section = definition.section
        row.prep_seconds = definition.prep_seconds
        row.answer_seconds = definition.answer_seconds
        row.ai_feedback = definition.ai_feedback
        row.tip = definition.tip
        row.instructions = definition.instructions
        row.sort_order = order
        db.add(row)
    db.flush()


def seed(db, sources: list[dict], questions: list[dict]) -> Counter:
    stats: Counter = Counter()
    upsert_task_types(db)

    existing_sources = {s.source_key: s for s in db.scalars(select(ContentSource))}
    for data in sources:
        source = existing_sources.get(data["source_key"])
        if source is None:
            source = ContentSource(source_key=data["source_key"])
            db.add(source)
            existing_sources[data["source_key"]] = source
            stats["sources_added"] += 1
        else:
            stats["sources_updated"] += 1
        source.kind = data["kind"]
        source.title = data["title"]
        source.body = data["body"]
        source.blank_markup = data.get("blank_markup")
        source.turns = data.get("turns")
    db.flush()

    existing_hashes = set(db.execute(select(Question.task_type_code, Question.content_hash)).all())
    for data in questions:
        code = data["type"]
        source_key = data.get("source_key")
        digest = content_hash(code, source_key, data["payload"])
        if (code, digest) in existing_hashes:
            stats["questions_unchanged"] += 1
            continue
        db.add(
            Question(
                task_type_code=code,
                source_id=existing_sources[source_key].id if source_key else None,
                payload=data["payload"],
                content_hash=digest,
                status=data.get("status", "active"),
                difficulty=data.get("difficulty"),
                report_count=0,
                times_served=0,
            )
        )
        existing_hashes.add((code, digest))
        stats["questions_added"] += 1
    db.flush()
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--min-active", type=int, default=30)
    parser.add_argument("--min-backup", type=int, default=15)
    args = parser.parse_args()

    sources, questions, files = load_bank(args.paths or None)
    report = validate_bank(sources, questions, args.min_active, args.min_backup)
    if report.errors:
        print("The question bank has problems. Run `python -m scripts.validate_bank` and fix them first.")
        for error in report.errors[:20]:
            print(f"  - {error}")
        return 1

    with session_factory()() as db:
        stats = seed(db, sources, questions)
        db.commit()
        print(f"Seeded from {len(files)} file(s): {dict(stats)}")
        counts: dict[str, Counter] = {}
        for code, status, n in db.execute(
            select(Question.task_type_code, Question.status, func.count()).group_by(Question.task_type_code, Question.status)
        ):
            counts.setdefault(code, Counter())[status] = n
        print(f"\n{'Type':<7}{'Active':>8}{'Backup':>8}{'Retired':>9}")
        for definition in TYPES:
            c = counts.get(definition.code, Counter())
            print(f"{definition.code:<7}{c['active']:>8}{c['backup']:>8}{c['retired']:>9}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
