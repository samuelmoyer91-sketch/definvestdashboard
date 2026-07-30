#!/usr/bin/env python3
"""Put disposable placeholder items in the triage queue, to time accept clicks.

The accept path is reported as taking 10-15s in production and the queue is
currently empty, so there is nothing to measure against. This seeds a handful
of obviously-fake items that exercise the real code path — including the
investor-link sync and the auto-reject scan — then removes every trace.

Everything it creates is marked with TEST_MARKER, in the title (so it is
unmistakable in the UI) and in relevance_flags (so cleanup is exact and can
never touch a real deal).

Usage, via .github/workflows/migrate.yml:
    python scripts/seed_timing_test.py --count 6
    python scripts/seed_timing_test.py --cleanup
    python scripts/seed_timing_test.py --status
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import (get_session, sync_turso, RawItem, ArticleContent,
                                 AIExtraction, MasterItem, RejectedItem, DealInvestor,
                                 Investor)

TEST_MARKER = "TIMING-TEST"
TITLE_PREFIX = "[TIMING TEST — safe to accept or reject]"

# Every investor name used below, so cleanup can remove the Investor entities
# that accepting a test item creates. Accepting runs _sync_investor_links(),
# which get-or-creates an Investor row; deleting only the DealInvestor links
# left "Acme Ventures" sitting on the /investors page with a stale deal_count.
SYNTHETIC_INVESTORS = {
    "Acme Ventures", "Beta Capital", "Gamma Partners", "Delta Fund",
    "Epsilon Ventures", "Zeta Capital", "Eta Growth", "Theta Ventures",
    "Iota Partners",
}

SAMPLES = [
    ("Placeholder Alpha Systems", "$25,000,000", "Acme Ventures (lead), Beta Capital",
     "Autonomous Systems/Drones,Sensors/ISR", "Austin, TX, USA"),
    ("Placeholder Bravo Dynamics", "$12,500,000", "Gamma Partners",
     "Electronic Warfare,Communications", "Huntsville, AL, USA"),
    ("Placeholder Charlie Robotics", "$40,000,000", "Delta Fund, Epsilon Ventures (lead)",
     "Autonomous Systems/Drones,AI/ML", "San Diego, CA, USA"),
    ("Placeholder Delta Aerospace", "$8,000,000", "Zeta Capital",
     "Aerospace,Manufacturing/Production", "Wichita, KS, USA"),
    ("Placeholder Echo Sensing", "$60,000,000", "Eta Growth (lead), Theta Ventures",
     "Sensors/ISR,Semiconductors/Electronics", "Boston, MA, USA"),
    ("Placeholder Foxtrot Marine", "$18,000,000", "Iota Partners",
     "Maritime/Naval,Autonomous Systems/Drones", "Norfolk, VA, USA"),
]


def seeded_items(session):
    return (session.query(RawItem)
            .filter(RawItem.relevance_flags.like(f"%{TEST_MARKER}%"))
            .all())


def do_status(session):
    items = seeded_items(session)
    print(f"{len(items)} seeded test items")
    for r in items:
        master = session.query(MasterItem).filter_by(item_id=r.id).first()
        rejected = session.query(RejectedItem).filter_by(item_id=r.id).first()
        state = "ACCEPTED" if master else ("REJECTED" if rejected else "in queue")
        print(f"   raw#{r.id:<6} {state:<10} {r.title[:58]}")
    return 0


def do_seed(session, count):
    existing = seeded_items(session)
    if existing:
        print(f"{len(existing)} test items already present — run --cleanup first")
        return do_status(session)

    now = datetime.utcnow()
    made = []
    for i, (company, amount, investors, sectors, location) in enumerate(SAMPLES[:count]):
        raw = RawItem(
            url=f"https://example.invalid/timing-test/{TEST_MARKER.lower()}-{i}",
            title=f"{TITLE_PREFIX} {company} Raises {amount}",
            rss_summary="Synthetic item created to measure triage accept latency.",
            published_date=now - timedelta(days=i),
            feed_source="Timing Test (synthetic)",
            date_found=now,
            status="scraped",
            relevance_score=1.0,
            relevance_flags=TEST_MARKER,
        )
        session.add(raw)
        session.flush()

        session.add(ArticleContent(
            item_id=raw.id,
            clean_text=("Synthetic article body for latency measurement. " * 40),
            scraped_at=now,
            scrape_success=True,
        ))
        session.add(AIExtraction(
            item_id=raw.id,
            title=raw.title,
            company=company,
            deal_amount=amount,
            investors=investors,
            sectors=sectors,
            capital_sources="Venture Capital",
            location=location,
            ai_summary=("Placeholder summary. This item is synthetic and exists only to "
                        "time the accept path. Accept or reject it freely; a cleanup "
                        "job removes it and anything it created."),
            strategic_significance="None — synthetic test item.",
            confidence_score=1.0,
            extracted_at=now,
            model_used="none (seeded)",
            summary_complete=True,
        ))
        made.append(raw.id)

    session.commit()
    sync_turso()
    print(f"Seeded {len(made)} test items into the triage queue: {made}")
    print("Accept them in the UI, then read /health, then run --cleanup.")
    return 0


def do_cleanup(session):
    items = seeded_items(session)
    if not items:
        print("Nothing to clean up.")
        return 0

    ids = [r.id for r in items]
    masters = session.query(MasterItem).filter(MasterItem.item_id.in_(ids)).all()
    master_ids = [m.id for m in masters]

    # Order matters: investor links reference master rows.
    if master_ids:
        (session.query(DealInvestor)
         .filter(DealInvestor.master_item_id.in_(master_ids))
         .delete(synchronize_session=False))
    for m in masters:
        session.delete(m)
    (session.query(RejectedItem).filter(RejectedItem.item_id.in_(ids))
     .delete(synchronize_session=False))
    (session.query(ArticleContent).filter(ArticleContent.item_id.in_(ids))
     .delete(synchronize_session=False))
    (session.query(AIExtraction).filter(AIExtraction.item_id.in_(ids))
     .delete(synchronize_session=False))
    for r in items:
        session.delete(r)

    session.flush()

    # Drop synthetic investors that no longer have any links. Guarded twice:
    # the name must be one we invented AND it must have zero remaining deals,
    # so a real investor can never be caught by this.
    removed_investors = []
    for inv in session.query(Investor).filter(Investor.name.in_(SYNTHETIC_INVESTORS)).all():
        remaining = (session.query(DealInvestor)
                     .filter_by(investor_id=inv.id).count())
        if remaining == 0:
            removed_investors.append(inv.name)
            session.delete(inv)

    session.commit()
    sync_turso()

    left = len(seeded_items(session))
    print(f"Removed {len(ids)} test items and {len(masters)} master rows they created.")
    if removed_investors:
        print(f"Removed {len(removed_investors)} synthetic investors: "
              f"{', '.join(sorted(removed_investors))}")
    print(f"Remaining seeded items: {left}")
    return 0 if left == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=6)
    ap.add_argument("--cleanup", action="store_true")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    session = get_session()
    try:
        if args.cleanup:
            return do_cleanup(session)
        if args.status:
            return do_status(session)
        return do_seed(session, max(1, min(args.count, len(SAMPLES))))
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
