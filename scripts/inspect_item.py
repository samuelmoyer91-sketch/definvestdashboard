#!/usr/bin/env python3
"""Show the full pipeline state of items matching a search term.

A run that loses its Turso connection part-way can leave an item written at
one stage but not the next — a raw_items row with no article text, or article
text with no extraction. Those surface in triage as a card with a raw RSS
title and nothing filled in, which looks like a scraper bug but is not.

    gh workflow run migrate.yml -f script=inspect_item.py -f args="Relativity"
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import (get_session, RawItem, ArticleContent,
                                 AIExtraction, MasterItem, RejectedItem)

term = sys.argv[1] if len(sys.argv) > 1 else 'Relativity'
session = get_session()

rows = (session.query(RawItem)
        .filter(RawItem.title.ilike(f'%{term}%'))
        .order_by(RawItem.id.desc()).limit(10).all())

print(f"{len(rows)} raw_items matching {term!r}\n" + "=" * 72)
for r in rows:
    art = session.query(ArticleContent).filter_by(item_id=r.id).first()
    ext = session.query(AIExtraction).filter_by(item_id=r.id).first()
    mas = session.query(MasterItem).filter_by(item_id=r.id).first()
    rej = session.query(RejectedItem).filter_by(item_id=r.id).first()
    print(f"\nid={r.id}  status={r.status}  found={r.date_found}")
    print(f"  title    : {r.title!r}")
    print(f"  feed     : {r.feed_source}")
    print(f"  url      : {r.url[:100]}")
    print(f"  relevance: {r.relevance_score}  flags={(r.relevance_flags or '')[:60]}")
    if art:
        txt = art.clean_text or ''
        print(f"  article  : success={art.scrape_success} len={len(txt):,} err={art.error_message!r}")
        print(f"             text[:200]={txt[:200]!r}")
    else:
        print("  article  : NO ROW (never scraped)")
    if ext:
        print(f"  extract  : company={ext.company!r} amount={ext.deal_amount!r} complete={ext.summary_complete}")
    else:
        print("  extract  : NO ROW")
    print(f"  accepted={bool(mas)}  rejected={bool(rej)}")

# Items from today that are in an inconsistent half-written state
from datetime import datetime, timedelta
cutoff = datetime.utcnow() - timedelta(days=1)
orphans = (session.query(RawItem)
           .outerjoin(ArticleContent, ArticleContent.item_id == RawItem.id)
           .filter(RawItem.date_found >= cutoff,
                   RawItem.status == 'scraped',
                   ArticleContent.id == None).count())
print(f"\n{'=' * 72}\nitems from the last 24h with status='scraped' but NO article row: {orphans}")
print("(non-zero means a run died between writing the item and its text)")
session.close()
