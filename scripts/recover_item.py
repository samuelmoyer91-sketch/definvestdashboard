#!/usr/bin/env python3
"""Return a rejected item to the triage queue, optionally re-extracting it.

Rejection is otherwise one-way: nothing in the app deletes a RejectedItem and
/rejected is view-only. That is fine for an ordinary reject, but an item can be
auto-rejected by the accept-time company-match scan while you were part-way
through something else with it — which is how the first roundup split was lost.

    --clear-split   drop split_instruction / split_parent_id, so the article
                    goes back to being an ordinary un-split card
    --reextract     re-run extraction afterwards (uses the focus if one is
                    still set, so run it WITH --clear-split to get a normal
                    unfocused extraction back)

Read-only unless --apply is passed.

    gh workflow run migrate.yml -f script=recover_item.py -f args="--item 14667"
    gh workflow run migrate.yml -f script=recover_item.py \
        -f args="--item 14667 --clear-split --reextract --apply"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import (get_session, sync_turso, RawItem, AIExtraction,
                                 MasterItem, RejectedItem)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--item', type=int, required=True, help='RawItem id')
    ap.add_argument('--clear-split', action='store_true')
    ap.add_argument('--reextract', action='store_true')
    ap.add_argument('--apply', action='store_true', help='without this, report only')
    args = ap.parse_args()

    session = get_session()
    item = session.query(RawItem).filter_by(id=args.item).first()
    if not item:
        print(f"No RawItem with id={args.item}")
        return 1

    rej = session.query(RejectedItem).filter_by(item_id=item.id).first()
    mas = session.query(MasterItem).filter_by(item_id=item.id).first()
    ext = session.query(AIExtraction).filter_by(item_id=item.id).first()

    print(f"id={item.id}  status={item.status}")
    print(f"  title  : {item.title[:70]}")
    print(f"  focus  : {item.split_instruction!r}")
    print(f"  parent : {item.split_parent_id}")
    print(f"  rejected: {bool(rej)}" + (f" — {rej.rejection_reason!r}" if rej else ""))
    print(f"  accepted: {bool(mas)}")
    if ext:
        print(f"  extraction: company={ext.company!r} complete={ext.summary_complete}")

    if mas:
        print("\nThis item is ACCEPTED. Remove the deal from /master first.")
        return 1

    actions = []
    if rej:
        actions.append("delete the RejectedItem row")
    if item.status != 'scraped':
        actions.append(f"set status '{item.status}' -> 'scraped'")
    if args.clear_split and (item.split_instruction or item.split_parent_id):
        actions.append("clear split_instruction / split_parent_id")
    if args.reextract:
        actions.append("re-extract")

    if not actions:
        print("\nNothing to do.")
        return 0

    print("\nWould:" if not args.apply else "\nApplying:")
    for a in actions:
        print(f"  - {a}")

    if not args.apply:
        print("\n(report only — pass --apply to make these changes)")
        return 0

    if rej:
        session.delete(rej)
    item.status = 'scraped'
    if args.clear_split:
        item.split_instruction = None
        item.split_parent_id = None
    session.commit()
    sync_turso()

    if args.reextract:
        from src.scraper.generate_ai_summaries import generate_summaries
        # force=True: the row may still carry a complete-but-wrong extraction,
        # which the normal "needs a summary" filter would skip.
        generate_summaries(item_ids=[item.id])
        sync_turso()

    session2 = get_session()
    check = session2.query(RawItem).filter_by(id=args.item).first()
    still = session2.query(RejectedItem).filter_by(item_id=args.item).first()
    ext2 = session2.query(AIExtraction).filter_by(item_id=args.item).first()
    print(f"\nOK: status={check.status} rejected={bool(still)} "
          f"focus={check.split_instruction!r}")
    if ext2:
        print(f"    extraction: company={ext2.company!r} amount={ext2.deal_amount!r} "
              f"complete={ext2.summary_complete}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
