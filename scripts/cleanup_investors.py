#!/usr/bin/env python3
"""Cleanup garbled investor records by re-syncing affected deals.

Garbled names come from AI extraction pre-populating the field with raw prose
(e.g. "backed by Renovus Capital Partners"). Rather than deleting, this script
re-runs the investor parser on each affected deal so clean records are created
(e.g. "Renovus Capital Partners"), then removes any garbled records with no
remaining links.

Usage:
    python scripts/cleanup_investors.py          # Preview only (dry run)
    python scripts/cleanup_investors.py --fix    # Re-sync and clean up
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_session, sync_turso, Investor, DealInvestor, MasterItem

# Leading phrases that signal prose, not a real investor name
LEADING_PHRASES = re.compile(
    r'^(?:'
    r'also\s+including|including|as\s+well\s+as|along\s+with|alongside'
    r'|backed\s+by|led\s+by|co-?led\s+by|joined\s+by'
    r'|with\s+participation\s+from|with\s+participation\s+by|with\s+previous\s+backers'
    r'|and\s+also|and|also|plus|with'
    r')\s+',
    re.IGNORECASE
)

# Substrings anywhere in the name that signal garbled prose
GARBAGE_SUBSTRINGS = [
    "as acquirer",
    "as seller",
    "new investors include",
    "existing backers",
    "related investment vehicles",
    "facility expansion",
    "expansion by",
    "under project",
]


def is_garbled(name: str) -> bool:
    if len(name) > 60:
        return True
    lower = name.lower()
    if LEADING_PHRASES.match(name):
        return True
    for phrase in GARBAGE_SUBSTRINGS:
        if phrase in lower:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Re-sync garbled investor records.")
    parser.add_argument("--fix", action="store_true", help="Apply fixes (default: dry run)")
    args = parser.parse_args()

    # Import here so the app path is set up first
    from src.web.app import _sync_investor_links

    session = get_session()

    try:
        all_investors = session.query(Investor).order_by(Investor.name).all()
        flagged = [inv for inv in all_investors if is_garbled(inv.name)]

        if not flagged:
            print("✓ No garbled investor records found.")
            return

        # Collect affected master items (deduplicated)
        affected_masters = {}
        for inv in flagged:
            links = session.query(DealInvestor).filter_by(investor_id=inv.id).all()
            for link in links:
                master = session.query(MasterItem).filter_by(id=link.master_item_id).first()
                if master and master.id not in affected_masters:
                    affected_masters[master.id] = master

        print(f"Found {len(flagged)} garbled investor record(s) across {len(affected_masters)} deal(s):\n")
        for inv in flagged:
            print(f"  {inv.name!r}")

        if affected_masters:
            print(f"\nAffected deals (will be re-synced):")
            for master in affected_masters.values():
                print(f"  Deal #{master.id}  investors={master.investors!r}")

        if not args.fix:
            print(f"\n(Dry run — pass --fix to re-sync and clean up)")
            return

        # Re-sync each affected deal — this re-parses master.investors with the
        # improved parser, creates clean Investor records, and removes old links
        print(f"\nRe-syncing {len(affected_masters)} deal(s)…")
        for master in affected_masters.values():
            _sync_investor_links(session, master)
            print(f"  ✓ Deal #{master.id}: {master.investors!r}")

        session.commit()

        # Delete any garbled investor records that now have zero links
        still_garbled = session.query(Investor).all()
        orphaned = [
            inv for inv in still_garbled
            if is_garbled(inv.name)
            and session.query(DealInvestor).filter_by(investor_id=inv.id).count() == 0
        ]
        if orphaned:
            print(f"\nRemoving {len(orphaned)} now-orphaned garbled record(s):")
            for inv in orphaned:
                print(f"  ✗ {inv.name!r}")
                session.delete(inv)
            session.commit()

        sync_turso()
        print("\n✓ Done. Sync pushed to Turso.")

    finally:
        session.close()


if __name__ == "__main__":
    main()
