#!/usr/bin/env python3
"""Report every split pass and why it is, or is not, in the triage queue.

The triage queue applies nine separate filters. A split pass that fails any
one of them silently disappears, which looks identical to the split not having
worked. This checks each filter individually and also reports the pass's rank
in the queue ordering — a pass over an older article is genuinely in the queue
but can sit below TRIAGE_PAGE_SIZE, which also looks like nothing happened.

Read-only. Run via:
    gh workflow run migrate.yml -f script=diagnose_splits.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import (get_session, RawItem, ArticleContent,
                                 AIExtraction, MasterItem, RejectedItem)

UNKNOWNS = ('unknown', 'n/a', 'none', '')


def main():
    session = get_session()

    passes = (session.query(RawItem)
              .filter((RawItem.split_parent_id.isnot(None)) |
                      (RawItem.split_instruction.isnot(None)))
              .order_by(RawItem.id).all())

    if not passes:
        print("No split passes found at all — the /split POST did not write rows.")
        print("Check the Railway logs for an exception in split_item().")
        return 0

    print(f"{len(passes)} split pass row(s) found\n" + "=" * 78)

    # Queue ordering is published_date desc, limited to 200 then sliced to 20.
    queue_order = [r.id for r in session.query(RawItem)
                   .join(ArticleContent, ArticleContent.item_id == RawItem.id)
                   .filter(ArticleContent.scrape_success == True,
                           RawItem.status != 'ai_screened_out')
                   .order_by(RawItem.published_date.desc()).limit(400).all()]

    for r in passes:
        art = session.query(ArticleContent).filter_by(item_id=r.id).first()
        ext = session.query(AIExtraction).filter_by(item_id=r.id).first()
        mas = session.query(MasterItem).filter_by(item_id=r.id).first()
        rej = session.query(RejectedItem).filter_by(item_id=r.id).first()

        print(f"\nid={r.id}  parent={r.split_parent_id}  status={r.status}")
        print(f"  url   : {r.url}")
        print(f"  focus : {r.split_instruction!r}")
        print(f"  date  : {r.published_date}")

        checks = [
            ("article text scraped",  bool(art and art.scrape_success)),
            ("not ai_screened_out",   r.status != 'ai_screened_out'),
            ("not already accepted",  mas is None),
            ("not already rejected",  rej is None),
        ]
        if ext:
            print(f"  extraction: company={ext.company!r} amount={ext.deal_amount!r}")
            print(f"              txn={ext.transaction_type!r} status={ext.deal_status!r} "
                  f"deployment={ext.capital_deployment!r} complete={ext.summary_complete}")
            allunk = all((getattr(ext, f) or '').strip().lower() in UNKNOWNS
                         for f in ('company', 'deal_amount', 'transaction_type'))
            checks += [
                ("txn is not Contract/Award", ext.transaction_type != 'Contract/Award'),
                ("txn is not IPO",            ext.transaction_type != 'IPO'),
                ("deal_status not speculative", ext.deal_status != 'speculative'),
                ("not transfer-without-amount",
                 not (ext.capital_deployment == 'transfer' and not ext.deal_amount)),
                ("not an all-Unknown stub",   not allunk),
            ]
        else:
            print("  extraction: NONE YET (re-extraction failed or has not run)")

        failed = [name for name, ok in checks if not ok]
        for name, ok in checks:
            print(f"    {'ok  ' if ok else 'FAIL'}  {name}")

        if failed:
            print(f"  => NOT IN QUEUE, filtered by: {', '.join(failed)}")
        elif r.id in queue_order:
            rank = queue_order.index(r.id) + 1
            where = "visible on page 1" if rank <= 20 else \
                    f"BELOW the 20 shown — scroll/older, rank {rank}"
            print(f"  => in queue, rank ~{rank} by date — {where}")
        else:
            print("  => passes all filters but is outside the 400 most recent by date")

    session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
