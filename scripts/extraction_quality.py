#!/usr/bin/env python3
"""Read-only: how often the AI leaves gaps or notes in the fields Sam reviews.

For extractions made in the last N days (default 30), reports:
  - location left blank / "Unknown", by deal type, and what happened to those
    cards (accepted with a location Sam typed, accepted blank, rejected, pending)
  - wording that describes what the article lacks ("not disclosed in the
    article", "paywall") in any field, with examples
  - investor values that are placeholders or unnamed groups

    gh workflow run migrate.yml -f script=extraction_quality.py -f args=--days=30
"""
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import (get_session, AIExtraction, RawItem,
                                 MasterItem, RejectedItem)

days = 30
for a in sys.argv[1:]:
    if a.startswith('--days='):
        days = int(a.split('=', 1)[1])
since = datetime.utcnow() - timedelta(days=days)

BLANK = {'', 'unknown', 'none', 'null', 'n/a', 'not specified', 'undisclosed'}
NOTE = re.compile(r"""(
    \b(the\s+)?(article|press\s+release|report|announcement|source|release|content|text)s?\b[^.]{0,60}?
        \b(does\s+not|doesn't|did\s+not|didn't|do\s+not|not|no|nor|without)\b
  | \bnot\s+(specified|disclosed|mentioned|stated|provided|available|reported|given|named|
            identified|detailed|clear|indicated|revealed|accessible)\b
  | \b(paywall|unspecified|unnamed|unidentified)\b
  | \bno\s+(details|information|specifics)\b
)""", re.I | re.X)
GROUP = re.compile(r"\b(unknown|undisclosed|unnamed|unspecified|various|existing|other|new|angel|"
                   r"strategic|institutional|private|individual|family\s+offices?|consortium|"
                   r"syndicate|group\s+of|several|multiple)\b[^,;]*\b(investors?|backers?|"
                   r"shareholders?|lenders?|offices?)\b|^\s*(unknown|undisclosed|n/?a|none)\s*$", re.I)

s = get_session()
rows = (s.query(AIExtraction, RawItem)
        .join(RawItem, AIExtraction.item_id == RawItem.id)
        .filter(AIExtraction.extracted_at >= since)
        .filter(RawItem.status != 'ai_screened_out')
        .all())
master = {m.item_id: m for m in s.query(MasterItem).filter(
    MasterItem.item_id.in_([r.id for _, r in rows])).all()} if rows else {}
rejected = {x.item_id for x in s.query(RejectedItem.item_id).filter(
    RejectedItem.item_id.in_([r.id for _, r in rows])).all()} if rows else set()

blank = lambda v: (v or '').strip().lower() in BLANK
print(f"Extractions in the last {days} days (excluding title-screened): {len(rows)}")

# --- Location -------------------------------------------------------------
no_loc = [(e, r) for e, r in rows if blank(e.location)]
print(f"\nLOCATION left blank/Unknown by the AI: {len(no_loc)} of {len(rows)} "
      f"({len(no_loc) / max(len(rows), 1):.0%})")
by_type = Counter(e.transaction_type or '?' for e, _ in no_loc)
all_type = Counter(e.transaction_type or '?' for e, _ in rows)
for t, n in by_type.most_common():
    print(f"  {t:24} {n:4} of {all_type[t]:4} ({n / all_type[t]:.0%})")
fates = Counter()
for e, r in no_loc:
    m = master.get(r.id)
    if m:
        fates['accepted, location typed in' if not blank(m.location) else 'ACCEPTED WITH NO LOCATION'] += 1
    elif r.id in rejected:
        fates['rejected'] += 1
    else:
        fates['still pending'] += 1
for k, n in fates.most_common():
    print(f"  -> {k}: {n}")
print("  examples (accepted; company -> location Sam entered):")
shown = 0
for e, r in no_loc:
    m = master.get(r.id)
    if m and not blank(m.location) and shown < 12:
        print(f"     {(e.company or '?')[:34]:34} -> {m.location[:40]}  [{e.transaction_type}]")
        shown += 1

# --- Notes about what the article lacks ------------------------------------
FIELDS = ['title', 'company', 'deal_amount', 'investors', 'location', 'strategic_significance']
print("\nNOTES ABOUT MISSING INFORMATION, by field (AI output):")
examples = []
for f in FIELDS:
    hits = [(e, r) for e, r in rows if getattr(e, f) and NOTE.search(getattr(e, f))]
    acc = sum(1 for _, r in hits if r.id in master)
    print(f"  {f:24} {len(hits):4} cards  ({acc} accepted)")
    for e, r in hits[:4]:
        v = getattr(e, f); m = NOTE.search(v); i = max(0, m.start() - 60)
        examples.append(f"     [{f}] #{r.id}: ...{v[i:m.end() + 50].strip()}...")
print("  examples:")
print("\n".join(examples[:16]))

# --- Investors ---------------------------------------------------------------
inv_blank = sum(1 for e, _ in rows if blank(e.investors))
print(f"\nINVESTORS blank/Unknown/Undisclosed: {inv_blank} of {len(rows)}")
groups = Counter()
for e, _ in rows:
    for part in re.split(r"\s*[,;]\s*|\s+and\s+", e.investors or ''):
        if part.strip() and GROUP.search(part):
            groups[part.strip()] += 1
print("  placeholder or unnamed-group values the AI wrote (count):")
for k, n in groups.most_common(20):
    print(f"    {n:3}  {k}")
raw_vals = Counter((e.investors or '').strip() for e, _ in rows if blank(e.investors))
print("  exact blank-ish values:", dict(raw_vals.most_common(6)))
