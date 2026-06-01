#!/usr/bin/env python3
"""
Duplicate-deal report for the master list.

READ-ONLY. This script never writes to the database, never touches the
ingest/triage/publish pipeline, and never deletes anything. It only reads
master_list, groups deals that look like the same underlying event, and
prints a report. You decide what (if anything) to merge or remove using
the existing edit UI.

Why this exists: the ingest dedup only catches exact-URL matches, so the
same deal reported by two outlets (different URLs) becomes two cards. For
a project that tallies capital deployed, that double-counts dollars.

Usage:
    python3 scripts/find_duplicates.py                # default report
    python3 scripts/find_duplicates.py --days 45      # wider time window
    python3 scripts/find_duplicates.py --published    # only published deals
    python3 scripts/find_duplicates.py --all-clusters # also show "probably distinct" groups

------------------------------------------------------------------------
TUNING KNOBS — change these and re-run; nothing else is affected.
------------------------------------------------------------------------
"""

import sys
import re
import argparse
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from src.database.models import get_session, MasterItem

# --- Tunable matching thresholds -----------------------------------------
WINDOW_DAYS = 30          # Two cards within this many days of each other
                          # are candidates for being the same deal.
AMOUNT_TOLERANCE = 0.05   # Amounts are "the same" if within 5% of each other.
                          # (Catches $28M vs $28.5M; raise to be looser.)

# Legal suffixes / filler stripped when comparing company names. We do NOT
# strip sector words like "aerospace" or "space" — those distinguish real
# companies (GE Aerospace vs GKN Aerospace), so removing them would create
# false merges.
NAME_NOISE = [
    'inc', 'incorporated', 'corp', 'corporation', 'llc', 'ltd', 'limited',
    'co', 'company', 'plc', 'lp', 'holdings', 'group', 'the',
]
# -------------------------------------------------------------------------


def normalize_company(name: str) -> str:
    """Lowercase, strip punctuation and legal suffixes for comparison."""
    if not name:
        return ''
    s = name.lower()
    s = s.replace('&amp;', '&')
    s = re.sub(r'[^\w\s]', ' ', s)          # punctuation -> space
    words = [w for w in s.split() if w not in NAME_NOISE]
    return ' '.join(words).strip()


def parse_amount(amount):
    """Parse a deal-amount string into a float number of dollars, or None.

    Handles: "$28,500,000", "$2M", "$1.3B", "250,000,000", "£19M", "€110M".
    Currency symbol is ignored (we treat the magnitude only — a known
    limitation; FX-converted figures may not match their source-currency
    twin, which the report will surface as a near-miss for you to judge).
    """
    if not amount:
        return None
    s = str(amount).strip().lower().replace(',', '')
    m = re.search(r'([\d.]+)\s*(b|billion|m|million|k|thousand)?', s)
    if not m:
        return None
    try:
        val = float(m.group(1))
    except ValueError:
        return None
    unit = m.group(2)
    if unit in ('b', 'billion'):
        val *= 1_000_000_000
    elif unit in ('m', 'million'):
        val *= 1_000_000
    elif unit in ('k', 'thousand'):
        val *= 1_000
    return val


def amounts_match(a, b) -> bool:
    """True if two parsed amounts are within tolerance, or both missing."""
    if a is None and b is None:
        return True          # both no-dollar -> treat as match candidate
    if a is None or b is None:
        return False         # one has a number, one doesn't -> not a match
    if a == 0 or b == 0:
        return a == b
    return abs(a - b) / max(a, b) <= AMOUNT_TOLERANCE


def fmt_amount(val):
    if val is None:
        return '(no $)'
    if val >= 1_000_000_000:
        return f'${val/1_000_000_000:.2f}B'
    if val >= 1_000_000:
        return f'${val/1_000_000:.1f}M'
    return f'${val:,.0f}'


def classify_cluster(entries):
    """Given all entries for one normalized company, return (likely_dup_pairs,
    is_likely_dup). A pair is a likely duplicate if amounts match AND the
    curate dates are within WINDOW_DAYS."""
    pairs = []
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            a, b = entries[i], entries[j]
            if a['date'] and b['date']:
                gap = abs((a['date'] - b['date']).days)
            else:
                gap = 9999
            if gap <= WINDOW_DAYS and amounts_match(a['amount_num'], b['amount_num']):
                pairs.append((a, b, gap))
    return pairs


def main():
    global WINDOW_DAYS
    ap = argparse.ArgumentParser(description='Read-only duplicate-deal report.')
    ap.add_argument('--days', type=int, default=WINDOW_DAYS,
                    help=f'Time window in days (default {WINDOW_DAYS})')
    ap.add_argument('--published', action='store_true',
                    help='Only consider published deals')
    ap.add_argument('--all-clusters', action='store_true',
                    help='Also list companies with multiple cards that look like DISTINCT deals')
    args = ap.parse_args()
    WINDOW_DAYS = args.days

    session = get_session()
    q = session.query(MasterItem)
    if args.published:
        q = q.filter(MasterItem.published == True)  # noqa: E712
    rows = q.all()

    # Build lightweight records
    deals = []
    for r in rows:
        deals.append({
            'id': r.id,
            'company': r.company or r.title or '(unknown)',
            'norm': normalize_company(r.company or r.title),
            'amount_raw': r.investment_amount,
            'amount_num': parse_amount(r.investment_amount),
            'date': r.curated_at or r.published_at,
            'title': r.title or r.company or '',
            'source': r.source_url or '',
        })

    # Group by normalized company name
    groups = {}
    for d in deals:
        if not d['norm']:
            continue
        groups.setdefault(d['norm'], []).append(d)
    multi = {k: sorted(v, key=lambda x: x['date'] or datetime.min)
             for k, v in groups.items() if len(v) > 1}

    likely_dups = []   # clusters with at least one matching pair
    distinct = []      # companies with multiple cards but no matching pair
    for norm, entries in multi.items():
        pairs = classify_cluster(entries)
        if pairs:
            likely_dups.append((norm, entries, pairs))
        else:
            distinct.append((norm, entries))

    # --- Report ----------------------------------------------------------
    print('=' * 78)
    print(f'DUPLICATE-DEAL REPORT  (window={WINDOW_DAYS}d, amount tolerance={AMOUNT_TOLERANCE:.0%})')
    print(f'{len(deals)} deals scanned | {len(likely_dups)} likely-duplicate clusters | '
          f'{len(distinct)} multi-card companies look distinct')
    print('=' * 78)

    total_overcount = 0.0
    for norm, entries, pairs in sorted(likely_dups, key=lambda x: -len(x[2])):
        # ids that appear in at least one matching pair — mark them with ">>"
        flagged = set()
        for a, b, gap in pairs:
            flagged.add(a['id'])
            flagged.add(b['id'])
        print(f'\n⚠  {entries[0]["company"]}  —  {len(entries)} cards, {len(pairs)} matching pair(s)')
        for d in entries:
            ds = d['date'].strftime('%Y-%m-%d') if d['date'] else '????-??-??'
            mark = '>>' if d['id'] in flagged else '  '
            print(f'  {mark} id={d["id"]:>4} | {ds} | {fmt_amount(d["amount_num"]):>8} | {d["title"][:58]}')
        if len(entries) > len(flagged):
            print(f'     (cards without ">>" share the company name but were not matched as dups)')
        # estimate double-counted dollars: for each matching pair, the smaller
        # of the two amounts is being counted twice
        for a, b, gap in pairs:
            amt = min(x for x in (a['amount_num'], b['amount_num']) if x) if (a['amount_num'] or b['amount_num']) else 0
            total_overcount += amt or 0

    print('\n' + '-' * 78)
    print(f'Estimated double-counted capital across likely-dup pairs: {fmt_amount(total_overcount)}')
    print('(Rough — assumes each matching pair double-counts the smaller amount.)')

    if args.all_clusters and distinct:
        print('\n' + '=' * 78)
        print('MULTI-CARD COMPANIES THAT LOOK LIKE DISTINCT DEALS (review, not flagged)')
        print('=' * 78)
        for norm, entries in sorted(distinct, key=lambda x: -len(x[1])):
            print(f'\nℹ  {entries[0]["company"]}  —  {len(entries)} cards')
            for d in entries:
                ds = d['date'].strftime('%Y-%m-%d') if d['date'] else '????-??-??'
                print(f'     id={d["id"]:>4} | {ds} | {fmt_amount(d["amount_num"]):>8} | {d["title"][:58]}')

    print('\nNothing was changed. Use the edit UI to merge/remove any confirmed duplicates.')
    session.close()


if __name__ == '__main__':
    main()
