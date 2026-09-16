"""Check every question bank file before seeding.

    python -m scripts.validate_bank                  # default files, needs 30 active + 15 backup per type
    python -m scripts.validate_bank path/to/file.json --min-active 0 --min-backup 0
"""

import argparse
import sys
from pathlib import Path

from app.bank.files import load_bank
from app.bank.validation import validate_bank
from app.task_types import TYPES


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path, help="Bank files or folders (default: reference file + seed/generated)")
    parser.add_argument("--min-active", type=int, default=30)
    parser.add_argument("--min-backup", type=int, default=15)
    args = parser.parse_args()

    sources, questions, files = load_bank(args.paths or None)
    if not files:
        print("No bank files found.")
        return 1
    print("Files:")
    for file in files:
        print(f"  {file}")
    report = validate_bank(sources, questions, args.min_active, args.min_backup)

    print(f"\n{len(sources)} sources, {len(questions)} questions\n")
    print(f"{'Type':<7}{'Active':>8}{'Backup':>8}{'Retired':>9}{'Total':>7}")
    for definition in TYPES:
        c = report.counts[definition.code]
        total = c["active"] + c["backup"] + c["retired"]
        print(f"{definition.code:<7}{c['active']:>8}{c['backup']:>8}{c['retired']:>9}{total:>7}")

    if report.errors:
        print(f"\n{len(report.errors)} problem(s):")
        for error in report.errors:
            print(f"  - {error}")
        return 1
    print("\nEverything looks good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
