#!/usr/bin/env python3
"""Show what text we are actually sending for the articles that get refused.

Every model refuses these with category=bio, including Haiku, which declines
conversationally rather than via the refusal mechanism. A European VC funding
roundup has no business tripping a biology classifier, so the likeliest
explanation is that the scraped text is not the article at all.

Read-only. Run via:
    gh workflow run migrate.yml -f script=inspect_failing_text.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import (get_session, RawItem, ArticleContent,
                                 AIExtraction)

session = get_session()

rows = (session.query(RawItem, ArticleContent)
        .join(ArticleContent, ArticleContent.item_id == RawItem.id)
        .join(AIExtraction, AIExtraction.item_id == RawItem.id)
        .filter(AIExtraction.summary_complete == False,
                ArticleContent.scrape_success == True)
        .order_by(RawItem.id).all())

print(f"{len(rows)} article(s) currently failing extraction\n")

feeds = {}
for item, _ in rows:
    feeds[item.feed_source] = feeds.get(item.feed_source, 0) + 1
print("by feed:")
for f, n in sorted(feeds.items(), key=lambda kv: -kv[1]):
    print(f"   {n:3d}  {f}")

print("\n" + "=" * 74)
print("Scraped text, first 900 chars of each (is this the article?)")
print("=" * 74)
for item, art in rows[:6]:
    txt = (art.clean_text or '')
    print(f"\n--- id={item.id}  feed={item.feed_source}")
    print(f"    title : {item.title[:70]}")
    print(f"    length: {len(txt):,} chars")
    print(f"    text  : {txt[:900]!r}")

session.close()
