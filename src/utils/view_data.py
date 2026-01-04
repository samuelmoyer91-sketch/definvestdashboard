"""Utility to view database contents."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import RawItem, get_session
from datetime import datetime


def view_raw_items(limit=10):
    """View raw RSS items."""
    session = get_session()

    print("=" * 80)
    print("RAW RSS ITEMS")
    print("=" * 80)
    print()

    items = session.query(RawItem).order_by(RawItem.date_found.desc()).limit(limit).all()

    for i, item in enumerate(items, 1):
        print(f"{i}. [{item.feed_source}]")
        print(f"   Title: {item.title}")
        print(f"   URL: {item.url}")
        print(f"   Published: {item.published_date}")
        print(f"   Summary: {item.rss_summary[:200]}..." if item.rss_summary and len(item.rss_summary) > 200 else f"   Summary: {item.rss_summary}")
        print()

    total = session.query(RawItem).count()
    print(f"Showing {len(items)} of {total} total items")
    print()

    session.close()


def stats():
    """Show database statistics."""
    session = get_session()

    total_items = session.query(RawItem).count()

    print("=" * 80)
    print("DATABASE STATISTICS")
    print("=" * 80)
    print()
    print(f"Total raw items: {total_items}")

    # Count by feed source
    from sqlalchemy import func
    feed_counts = session.query(
        RawItem.feed_source,
        func.count(RawItem.id)
    ).group_by(RawItem.feed_source).all()

    print()
    print("Items by feed:")
    for feed, count in feed_counts:
        print(f"  {feed}: {count}")

    session.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'stats':
        stats()
    else:
        limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        view_raw_items(limit)
