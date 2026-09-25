#!/usr/bin/env python3
"""List deals removed from the public site (soft-deleted), newest first.

Read-only. Shows when and why each was removed, so a batch of removals can be
checked for intent (e.g. 2026-09-25: eight Northrop Grumman deals).

    gh workflow run migrate.yml -f script=list_removed.py -f args="--days 7"
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import get_session, MasterItem


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=30)
    args = ap.parse_args()
    since = datetime.utcnow() - timedelta(days=args.days)
    session = get_session()
    rows = (session.query(MasterItem)
            .filter(MasterItem.removed_at.isnot(None), MasterItem.removed_at >= since)
            .order_by(MasterItem.removed_at.desc()).all())
    print(f"{len(rows)} deal(s) removed in the last {args.days} days\n")
    for m in rows:
        print(f"#{m.id:<5} removed {m.removed_at:%Y-%m-%d %H:%M} UTC  reason={m.removed_reason!r}")
        print(f"       {m.title or m.company}  | {m.investment_amount or '(no $)'} | {m.location}")
    session.close()


if __name__ == '__main__':
    main()
