#!/usr/bin/env python3
"""Apply reviewed corrections to master_list fields.

The general form of fix_currency_amounts.py (2026-09-24). A JSON file lists
{id, field, old, new, why}. Each row is applied only if the stored value still
equals `old`, so a deal edited since the review is skipped, not overwritten,
and re-running is safe. Only the fields in ALLOWED can be touched.

Runs in GitHub Actions via migrate.yml (the only place with Turso credentials):
    script: fix_master_fields.py   args: --file scripts/data/<file>.json            (dry run)
    script: fix_master_fields.py   args: --file scripts/data/<file>.json --apply
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import get_session, MasterItem

ALLOWED = {'investment_amount', 'location', 'title'}


def same(a, b):
    return (a or '') == (b or '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', required=True)
    ap.add_argument('--apply', action='store_true', help='without this, report only')
    args = ap.parse_args()

    fixes = json.loads(Path(args.file).read_text(encoding='utf-8'))
    bad = [f for f in fixes if f['field'] not in ALLOWED]
    if bad:
        print(f"Refusing: fields not allowed: {sorted({f['field'] for f in bad})}")
        return 1

    session = get_session()
    applied = skipped = 0
    try:
        for f in fixes:
            m = session.query(MasterItem).filter_by(id=f['id']).first()
            current = getattr(m, f['field']) if m else None
            if not m or not same(current, f['old']):
                skipped += 1
                print(f"SKIP  #{f['id']:<5} {f['field']}: stored {current!r}, expected {f['old']!r}")
                continue
            print(f"{'FIX  ' if args.apply else 'WOULD'} #{f['id']:<5} {f['field']}: {f['old']!r} -> {f['new']!r}")
            if args.apply:
                setattr(m, f['field'], f['new'])
            applied += 1
        if args.apply:
            session.commit()
    finally:
        session.close()

    print(f"\n{'applied' if args.apply else 'would apply'}: {applied}   skipped: {skipped}   total: {len(fixes)}")
    return 1 if (skipped and args.apply) else 0


if __name__ == '__main__':
    sys.exit(main())
