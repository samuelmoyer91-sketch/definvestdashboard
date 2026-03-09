#!/usr/bin/env python3
"""
Run AI title screening on pending RSS items.

Screens articles by title + RSS summary before scraping. Items flagged as
not relevant get status='ai_screened_out' and are skipped by the scraper
and AI extraction steps.

Usage:
    python3 src/scraper/run_title_screen.py           # Screen all pending
    python3 src/scraper/run_title_screen.py --dry-run  # Preview without updating DB
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import RawItem, ArticleContent, ApiUsageLog, get_session
from src.utils.title_screener import screen_titles

HAIKU_MODEL = "claude-haiku-4-5-20251001"
HAIKU_INPUT_PRICE = 0.80   # $ per 1M tokens
HAIKU_OUTPUT_PRICE = 4.00  # $ per 1M tokens


def run_title_screen(dry_run=False):
    """
    Screen all unscraped 'new' items by title.

    Items that pass keep status='new' (scraper will pick them up).
    Items that fail get status='ai_screened_out' (skipped by scraper).
    """
    session = get_session()

    # Get items that are 'new' and haven't been scraped yet
    items = session.query(RawItem).filter(
        RawItem.status == 'new',
        ~RawItem.id.in_(
            session.query(ArticleContent.item_id)
        )
    ).order_by(RawItem.id.desc()).all()

    if not items:
        print("No items to screen.")
        session.close()
        return 0, 0

    print("=" * 70)
    print(f"AI TITLE SCREENING - {len(items)} items")
    print("=" * 70)
    print()

    # Prepare items for screening
    screen_input = [
        {
            'id': item.id,
            'title': item.title,
            'summary': item.rss_summary,
            'feed_source': item.feed_source
        }
        for item in items
    ]

    # Run AI screening
    results, total_input, total_output = screen_titles(screen_input)

    # Apply results
    passed = 0
    screened_out = 0

    for item in items:
        result = results.get(item.id, {"relevant": True, "reason": "No result"})

        if result["relevant"]:
            passed += 1
        else:
            screened_out += 1
            if not dry_run:
                item.status = 'ai_screened_out'
            prefix = "[DRY RUN] " if dry_run else ""
            print(f"  {prefix}Screened out: {item.title[:70]}...")
            print(f"    Reason: {result['reason']}")

    if not dry_run:
        session.commit()

        # Log API usage
        try:
            cost = (total_input * HAIKU_INPUT_PRICE + total_output * HAIKU_OUTPUT_PRICE) / 1_000_000
            log = ApiUsageLog(
                logged_at=datetime.utcnow(),
                run_type='title_screen',
                model=HAIKU_MODEL,
                items_processed=len(items),
                input_tokens=total_input,
                output_tokens=total_output,
                cost_usd=cost,
            )
            session.add(log)
            session.commit()
            print(f"  API usage logged: {total_input:,} in / {total_output:,} out — ${cost:.4f}")
        except Exception as e:
            print(f"  Warning: failed to log API usage: {e}")

    print()
    print("=" * 70)
    print(f"RESULTS: {passed} passed, {screened_out} screened out")
    if dry_run:
        print("(Dry run — no changes saved)")
    print("=" * 70)

    session.close()
    return passed, screened_out


if __name__ == '__main__':
    import os
    os.chdir(Path(__file__).parent.parent.parent)

    dry_run = '--dry-run' in sys.argv

    run_title_screen(dry_run=dry_run)
