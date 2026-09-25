#!/usr/bin/env python3
"""Propose titles for published deals that have none.

68 early deals (Jan–Feb 2026, before the AI wrote titles) have a blank
master_list.title, so the public site falls back to the raw article headline,
publisher suffix and all. This asks the model for a title in the same house
style as every other deal (ai_summarizer.TITLE_RULES), from the headline plus
what was curated for the deal.

It NEVER writes. It prints the proposals as JSON for review; the reviewed file
is then applied with fix_master_fields.py.

    gh workflow run migrate.yml -f script=fill_missing_titles.py
"""
import html
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from anthropic import Anthropic

from src.database.models import get_session, MasterItem, RawItem
from src.utils.ai_summarizer import TITLE_RULES


def clean_headline(t):
    t = html.unescape(re.sub(r'<[^>]+>', '', t or ''))
    return re.split(r'\s+[-|–—]\s+(?=[A-Z][\w\s.]*$)', t)[0].strip()


def main():
    client = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
    session = get_session()
    rows = (session.query(MasterItem, RawItem)
            .join(RawItem, MasterItem.item_id == RawItem.id)
            .filter(MasterItem.removed_at.is_(None))
            .order_by(MasterItem.id).all())
    blank = [(m, r) for m, r in rows if not (m.title or '').strip()]
    print(f"{len(blank)} published deal(s) without a title\n")

    proposals = []
    for m, r in blank:
        headline = clean_headline(r.title)
        facts = "\n".join(f"{k}: {v}" for k, v in (
            ("Original headline", headline), ("Company", m.company),
            ("Amount", m.investment_amount), ("Investors", m.investors),
            ("Location", m.location), ("Summary", m.summary)) if v)
        msg = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=200,
            messages=[{"role": "user", "content":
                       f"Write the title for this defense-investment deal.\n\n"
                       f"TITLE RULES: {TITLE_RULES}\n\n{facts}\n\n"
                       f"Reply with the title only — no quotes, no commentary."}],
        )
        text = next((b.text for b in msg.content if b.type == "text"), "").strip().strip('"')
        if not text:
            print(f"  #{m.id}: no title returned ({msg.stop_reason})")
            continue
        proposals.append({"id": m.id, "field": "title", "old": m.title or "", "new": text,
                          "why": f"headline: {headline}"})
        print(f"  #{m.id:<4} {headline[:60]!r}\n        -> {text}")
    session.close()

    print("\n=== PROPOSALS JSON ===")
    print(json.dumps(proposals, ensure_ascii=False))
    print("=== END ===")


if __name__ == '__main__':
    main()
