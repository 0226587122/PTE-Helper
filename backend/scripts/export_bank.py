"""Write the whole question bank (every status) back to JSON, in the same shape as the seed files.

    python -m scripts.export_bank --out bank-export.json
    python -m scripts.export_bank            # writes bank-export-YYYYMMDD-HHMMSS.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.db import session_factory
from app.models import ContentSource, Question


def export(db) -> dict:
    sources = [
        {
            k: v
            for k, v in {
                "source_key": s.source_key,
                "kind": s.kind,
                "title": s.title,
                "body": s.body,
                "blank_markup": s.blank_markup,
                "turns": s.turns,
            }.items()
            if v is not None
        }
        for s in db.scalars(select(ContentSource).order_by(ContentSource.source_key))
    ]
    questions = []
    for q in db.scalars(select(Question).order_by(Question.task_type_code, Question.id)):
        item = {"type": q.task_type_code}
        if q.source is not None:
            item["source_key"] = q.source.source_key
        item["status"] = q.status
        if q.difficulty is not None:
            item["difficulty"] = q.difficulty
        item["payload"] = q.payload
        item["id"] = q.id
        item["report_count"] = q.report_count
        item["times_served"] = q.times_served
        questions.append(item)
    return {
        "version": 1,
        "notes": f"Exported from the database at {datetime.now(timezone.utc).isoformat(timespec='seconds')}. "
        "The id, report_count and times_served fields are for reference; the seed script ignores them.",
        "sources": sources,
        "questions": questions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    out = args.out or Path(f"bank-export-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.json")
    with session_factory()() as db:
        data = export(db)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(data['sources'])} sources and {len(data['questions'])} questions to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
