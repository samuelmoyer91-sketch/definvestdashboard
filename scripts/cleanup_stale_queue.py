"""
One-off script: mark stale 'new' items as auto_rejected.

Targets raw_items where:
  - status = 'new'
  - published_date is not null AND older than MAX_AGE_DAYS

Run from project root:
  python scripts/cleanup_stale_queue.py

Requires TURSO_DATABASE_URL + TURSO_AUTH_TOKEN env vars for cloud,
or falls back to local databases/tracker.db.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.database import RawItem, get_session, sync_turso

MAX_AGE_DAYS = 7

def main():
    print("Cleanup: marking stale queue items as auto_rejected")
    print(f"Cutoff: items with published_date older than {MAX_AGE_DAYS} days")
    print()

    session = get_session()
    sync_turso()

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)

    candidates = session.query(RawItem).filter(
        RawItem.status.in_(['new', 'scraped']),
        RawItem.published_date != None,
        RawItem.published_date < cutoff.replace(tzinfo=None)  # DB stores naive datetimes
    ).all()

    print(f"Found {len(candidates)} stale items to clean up.")

    if not candidates:
        print("Nothing to do.")
        return

    # Show a sample before committing
    print("\nSample (first 10):")
    for item in candidates[:10]:
        print(f"  [{item.published_date.date()}] {item.title[:70]}")

    print()
    confirm = input(f"Mark all {len(candidates)} items as auto_rejected? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Aborted.")
        return

    for item in candidates:
        item.status = 'auto_rejected'
        item.relevance_flags = (item.relevance_flags or '') + ',stale'

    session.commit()
    print(f"\nDone. {len(candidates)} items marked auto_rejected.")
    session.close()


if __name__ == '__main__':
    main()
