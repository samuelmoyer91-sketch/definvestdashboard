#!/usr/bin/env python3
"""Apply reviewed corrections to master_items.investment_amount.

Created 2026-09-24 for OPEN_ITEMS #0: deals accepted before the 2026-08
currency fix were stored with their euro/pound symbol stripped (and sometimes
their magnitude too, e.g. "€300M" stored as "$300"). The corrections file was
built from each deal's own title and reviewed by Sam before running.

Each row is applied only if the stored value still equals `old`, so a deal
edited since the review is skipped rather than overwritten. Re-running is safe:
already-fixed rows no longer match `old` and are reported as skipped.

Runs in GitHub Actions via migrate.yml (the only place with Turso credentials):
    script: fix_currency_amounts.py   args: --dry-run
    script: fix_currency_amounts.py   args: (none)  -> writes
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import get_session, MasterItem

DEFAULT_FILE = Path(__file__).parent / "data" / "currency_fixes_2026-09-24.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DEFAULT_FILE))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    fixes = json.loads(Path(args.file).read_text(encoding="utf-8"))
    session = get_session()
    applied = skipped = 0
    try:
        for f in fixes:
            m = session.query(MasterItem).filter_by(id=f["id"]).first()
            current = m.investment_amount if m else None
            if current != f["old"]:
                skipped += 1
                print(f"SKIP  #{f['id']:<5} stored {current!r}, expected {f['old']!r}")
                continue
            print(f"{'WOULD' if args.dry_run else 'FIX  '} #{f['id']:<5} {f['old']:>16} -> {f['new']:<16} {f['company']}")
            if not args.dry_run:
                m.investment_amount = f["new"]
            applied += 1
        if not args.dry_run:
            session.commit()
    finally:
        session.close()

    verb = "would apply" if args.dry_run else "applied"
    print(f"\n{verb}: {applied}   skipped: {skipped}   total: {len(fixes)}")
    if skipped and not args.dry_run:
        sys.exit(1)


if __name__ == "__main__":
    main()
