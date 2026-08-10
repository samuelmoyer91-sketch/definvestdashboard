#!/usr/bin/env python3
"""Re-run AI extraction for specific items, or for every split pass.

Useful when extraction was skipped or failed for a known set — e.g. a roundup
split that ran while the app had no ANTHROPIC_API_KEY, so every pass came back
as an empty stub.

Each row's split_instruction is applied automatically, because
generate_summaries reads it from the row rather than taking it as an argument.

A failed extraction will NOT overwrite a good one: generate_summaries keeps the
existing values and only clears summary_complete, so re-running this is safe
even if some items fail.

    gh workflow run migrate.yml -f script=reextract_items.py -f args="--splits"
    gh workflow run migrate.yml -f script=reextract_items.py -f args="--splits --apply"
    gh workflow run migrate.yml -f script=reextract_items.py -f args="--items 14667,14839 --apply"
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import get_session, sync_turso, RawItem, AIExtraction


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--items', help='comma-separated RawItem ids')
    ap.add_argument('--splits', action='store_true',
                    help='every row carrying a split_instruction')
    ap.add_argument('--incomplete-only', action='store_true',
                    help='skip rows whose extraction is already complete')
    ap.add_argument('--apply', action='store_true', help='without this, report only')
    args = ap.parse_args()

    if not args.items and not args.splits:
        print("Nothing selected — pass --items or --splits.")
        return 1

    session = get_session()

    if args.splits:
        rows = (session.query(RawItem)
                .filter(RawItem.split_instruction.isnot(None))
                .order_by(RawItem.id).all())
    else:
        ids = [int(x) for x in args.items.split(',') if x.strip()]
        rows = session.query(RawItem).filter(RawItem.id.in_(ids)).all()

    selected = []
    for r in rows:
        ext = session.query(AIExtraction).filter_by(item_id=r.id).first()
        complete = bool(ext and ext.summary_complete)
        if args.incomplete_only and complete:
            print(f"  skip  id={r.id} (already complete)")
            continue
        selected.append(r.id)
        print(f"  id={r.id}  complete={complete}  focus={r.split_instruction!r}")

    if not selected:
        print("\nNothing to do.")
        return 0

    print(f"\n{len(selected)} item(s) to re-extract.")
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("ERROR: ANTHROPIC_API_KEY is not set — every extraction would "
              "return an empty stub. Aborting rather than burning the run.")
        return 1

    if not args.apply:
        print("(report only — pass --apply to run)")
        return 0

    from src.scraper.generate_ai_summaries import generate_summaries
    generate_summaries(item_ids=selected)
    sync_turso()

    check = get_session()
    print("\nAfter:")
    for i in selected:
        e = check.query(AIExtraction).filter_by(item_id=i).first()
        if e:
            print(f"  id={i}  company={e.company!r}  amount={e.deal_amount!r}  "
                  f"complete={e.summary_complete}")
        else:
            print(f"  id={i}  NO EXTRACTION ROW")
    return 0


if __name__ == "__main__":
    sys.exit(main())
