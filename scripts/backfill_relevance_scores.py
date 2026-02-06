#!/usr/bin/env python3
"""
Backfill relevance scores for existing database items.

Created: 2026-01-22
Purpose: Score existing items to evaluate filter effectiveness before going live.

Usage:
    python3 scripts/backfill_relevance_scores.py --dry-run   # Preview only
    python3 scripts/backfill_relevance_scores.py             # Actually update DB
"""

import sys
from pathlib import Path
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import RawItem, get_session
from src.utils.relevance_scorer import calculate_relevance_score, should_auto_reject, load_scoring_config


def backfill_scores(dry_run=True, verbose=True):
    """
    Calculate relevance scores for all existing items.

    Args:
        dry_run: If True, don't update database (just report)
        verbose: If True, print details for each item
    """
    config = load_scoring_config(str(project_root / 'config' / 'feeds.json'))
    session = get_session(str(project_root / 'databases' / 'tracker.db'))

    # Get all items
    items = session.query(RawItem).all()

    print("=" * 80)
    print(f"BACKFILL RELEVANCE SCORES {'(DRY RUN)' if dry_run else '(LIVE)'}")
    print(f"Processing {len(items)} items")
    print("=" * 80)
    print()

    # Stats
    stats = {
        'total': len(items),
        'would_keep': 0,
        'would_reject': 0,
        'by_feed': {},
        'high_score': [],  # Top scoring items
        'low_score': [],   # Items that would be rejected
    }

    for item in items:
        score, matched, excluded = calculate_relevance_score(
            item.title,
            item.rss_summary or '',
            config
        )

        reject, reason = should_auto_reject(score, matched, excluded)

        # Track by feed
        feed = item.feed_source or 'Unknown'
        if feed not in stats['by_feed']:
            stats['by_feed'][feed] = {'keep': 0, 'reject': 0, 'scores': []}

        stats['by_feed'][feed]['scores'].append(score)

        if reject:
            stats['would_reject'] += 1
            stats['by_feed'][feed]['reject'] += 1
            stats['low_score'].append({
                'title': item.title,
                'score': score,
                'reason': reason,
                'feed': feed
            })
        else:
            stats['would_keep'] += 1
            stats['by_feed'][feed]['keep'] += 1
            if score >= 0.4:
                stats['high_score'].append({
                    'title': item.title,
                    'score': score,
                    'matched': matched,
                    'feed': feed
                })

        # Update database if not dry run
        if not dry_run:
            item.relevance_score = score
            item.relevance_flags = ','.join(matched) if matched else None
            # Don't change status for existing items - let human review stand

    if not dry_run:
        session.commit()
        print("Database updated!\n")

    session.close()

    # Print summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total items: {stats['total']}")
    print(f"Would KEEP: {stats['would_keep']} ({100*stats['would_keep']/stats['total']:.1f}%)")
    print(f"Would REJECT: {stats['would_reject']} ({100*stats['would_reject']/stats['total']:.1f}%)")
    print()

    print("BY FEED:")
    print("-" * 60)
    for feed, data in sorted(stats['by_feed'].items()):
        total = data['keep'] + data['reject']
        avg_score = sum(data['scores']) / len(data['scores']) if data['scores'] else 0
        reject_rate = 100 * data['reject'] / total if total > 0 else 0
        print(f"  {feed}:")
        print(f"    Keep: {data['keep']}, Reject: {data['reject']} ({reject_rate:.0f}% rejection rate)")
        print(f"    Avg score: {avg_score:.2f}")
    print()

    # Show high-scoring items
    print("TOP SCORING ITEMS (would definitely keep):")
    print("-" * 60)
    for item in sorted(stats['high_score'], key=lambda x: x['score'], reverse=True)[:10]:
        print(f"  [{item['score']:.2f}] {item['title'][:65]}...")
        print(f"         Matched: {', '.join(item['matched'][:5])}")
    print()

    # Show items that would be rejected
    print("SAMPLE ITEMS THAT WOULD BE AUTO-REJECTED:")
    print("-" * 60)
    for item in stats['low_score'][:15]:
        print(f"  [{item['score']:.2f}] {item['title'][:65]}...")
        print(f"         Reason: {item['reason']}")
    print()

    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backfill relevance scores for existing items')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Preview changes without updating database (default: True)')
    parser.add_argument('--live', action='store_true',
                        help='Actually update the database')

    args = parser.parse_args()

    # --live overrides --dry-run
    dry_run = not args.live

    if not dry_run:
        print("WARNING: This will update the database!")
        confirm = input("Type 'yes' to continue: ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)

    backfill_scores(dry_run=dry_run)
