"""
Duplicate-deal detection — shared logic.

Pure functions, no database. Used by BOTH:
  - scripts/find_duplicates.py  (CLI report)
  - src/web/app.py  /duplicates  (triage-app page)

Tune the matching behavior here, in ONE place, and both the command-line
report and the in-app page reflect the change. Nothing here writes to the
database or affects the pipeline — it only analyzes a list of deals.

------------------------------------------------------------------------
TUNING KNOBS
------------------------------------------------------------------------
"""

import re
from datetime import datetime

WINDOW_DAYS = 30          # Two cards within this many days are dup candidates.
AMOUNT_TOLERANCE = 0.05   # Amounts "match" if within 5% (catches $28M vs $28.5M).

# Legal suffixes / filler stripped when comparing company names. We do NOT
# strip sector words like "aerospace" or "space" — those distinguish real
# companies (GE Aerospace vs GKN Aerospace), so removing them would create
# false merges.
NAME_NOISE = [
    'inc', 'incorporated', 'corp', 'corporation', 'llc', 'ltd', 'limited',
    'co', 'company', 'plc', 'lp', 'holdings', 'group', 'the',
]
# -------------------------------------------------------------------------


def normalize_company(name):
    """Lowercase, strip punctuation and legal suffixes for comparison."""
    if not name:
        return ''
    s = name.lower().replace('&amp;', '&')
    s = re.sub(r'[^\w\s]', ' ', s)
    words = [w for w in s.split() if w not in NAME_NOISE]
    return ' '.join(words).strip()


def parse_amount(amount):
    """Parse a deal-amount string into dollars (float), or None.

    Handles "$28,500,000", "$2M", "$1.3B", "250,000,000", "£19M", "€110M".
    Currency symbol is ignored (magnitude only) — an FX-converted figure may
    not match its source-currency twin, which surfaces as a near-miss to judge.
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


def amounts_match(a, b, tolerance=AMOUNT_TOLERANCE):
    """True if two parsed amounts are within tolerance, or both missing."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if a == 0 or b == 0:
        return a == b
    return abs(a - b) / max(a, b) <= tolerance


def fmt_amount(val):
    if val is None:
        return '(no $)'
    if val >= 1_000_000_000:
        return f'${val/1_000_000_000:.2f}B'
    if val >= 1_000_000:
        return f'${val/1_000_000:.1f}M'
    return f'${val:,.0f}'


def find_clusters(deals, window_days=WINDOW_DAYS, tolerance=AMOUNT_TOLERANCE):
    """Group deals into duplicate clusters.

    Args:
        deals: list of dicts, each with keys:
            id, company, amount (raw string or None), date (datetime or None),
            title, source
        window_days: max day-gap for two cards to be a dup pair
        tolerance: amount match tolerance (fraction)

    Returns dict with:
        likely:   list of clusters that contain >=1 matching pair
        distinct: list of multi-card same-company clusters with NO matching pair
        overcount: estimated double-counted dollars across likely-dup pairs

    Each cluster is a dict:
        company, entries (sorted by date), pairs (list of (a,b,gap)),
        flagged_ids (set of ids in >=1 pair)
    Nothing is mutated; input deals are read only.
    """
    # enrich
    recs = []
    for d in deals:
        recs.append({
            'id': d.get('id'),
            'company': d.get('company') or d.get('title') or '(unknown)',
            'norm': normalize_company(d.get('company') or d.get('title')),
            'amount_num': parse_amount(d.get('amount')),
            'date': d.get('date'),
            'title': d.get('title') or d.get('company') or '',
            'source': d.get('source') or '',
        })

    groups = {}
    for r in recs:
        if r['norm']:
            groups.setdefault(r['norm'], []).append(r)

    likely, distinct, overcount = [], [], 0.0
    for norm, entries in groups.items():
        if len(entries) < 2:
            continue
        entries.sort(key=lambda x: x['date'] or datetime.min)
        pairs = []
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                a, b = entries[i], entries[j]
                gap = abs((a['date'] - b['date']).days) if (a['date'] and b['date']) else 9999
                if gap <= window_days and amounts_match(a['amount_num'], b['amount_num'], tolerance):
                    pairs.append((a, b, gap))
        if pairs:
            flagged = set()
            for a, b, _ in pairs:
                flagged.add(a['id'])
                flagged.add(b['id'])
                amt = min(x for x in (a['amount_num'], b['amount_num']) if x) if (a['amount_num'] or b['amount_num']) else 0
                overcount += amt or 0
            likely.append({'company': entries[0]['company'], 'entries': entries,
                           'pairs': pairs, 'flagged_ids': flagged})
        else:
            distinct.append({'company': entries[0]['company'], 'entries': entries,
                             'pairs': [], 'flagged_ids': set()})

    likely.sort(key=lambda c: -len(c['pairs']))
    distinct.sort(key=lambda c: -len(c['entries']))
    return {'likely': likely, 'distinct': distinct, 'overcount': overcount}


def _match_reason(group_entries, max_gap):
    """Human-readable why-flagged string, e.g. 'same company · ~$28.5M · within 8 days'."""
    parts = ['same company']
    amts = [e['amount_num'] for e in group_entries if e['amount_num']]
    if amts:
        parts.append('~' + fmt_amount(min(amts)))
    else:
        parts.append('no $ amount')
    if max_gap >= 9999:
        parts.append('date unknown')
    elif max_gap == 0:
        parts.append('same day')
    else:
        parts.append(f'within {max_gap} days')
    return ' · '.join(parts)


def find_queue_duplicates(queue_items, published_items,
                          window_days=WINDOW_DAYS, tolerance=AMOUNT_TOLERANCE):
    """Flag triage-queue items that look like duplicates of an already-published
    deal OR of another queue item, BEFORE Sam triages them.

    READ-ONLY / pure: computes from data passed in, mutates nothing, no DB.

    Args:
        queue_items:     list of dicts (id, company, amount, date, title, source,
                         location, insight) — items currently awaiting triage.
        published_items: same shape — deals already on the dashboard (master_list).
        window_days, tolerance: matching thresholds (defaults from this module).

    Returns dict:
        groups:        list of deal-groups, each a dict:
                          type: 'matches_published' | 'queue_only'
                          company: display name
                          reason: human match-reason string
                          confidence: float (higher = more certain; for sorting)
                          published: list of published entries (Type 1 anchors; [] for Type 2)
                          queue: list of queue entries (actionable; the dup candidates)
        flagged_ids:   set of queue-item ids that appear in any group
                       (these are the ones home() should pull OUT of the main queue)

    Only queue items that match something are flagged. A queue item that
    matches nothing stays in the normal triage flow (not returned here).
    """
    def enrich(d, origin):
        return {
            'id': d.get('id'),
            'origin': origin,
            'company': d.get('company') or d.get('title') or '(unknown)',
            'norm': normalize_company(d.get('company') or d.get('title')),
            'amount_num': parse_amount(d.get('amount')),
            'date': d.get('date'),
            'title': d.get('title') or d.get('company') or '',
            'source': d.get('source') or '',
            'location': d.get('location') or '',
            'insight': d.get('insight') or '',
        }

    recs = [enrich(d, 'queue') for d in queue_items] + \
           [enrich(d, 'published') for d in published_items]

    # group by company, then union matched pairs into connected components
    by_company = {}
    for r in recs:
        if r['norm']:
            by_company.setdefault(r['norm'], []).append(r)

    groups, flagged_ids = [], set()
    for norm, entries in by_company.items():
        if len(entries) < 2:
            continue
        n = len(entries)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            parent[find(a)] = find(b)

        pair_gaps = []
        for i in range(n):
            for j in range(i + 1, n):
                a, b = entries[i], entries[j]
                gap = abs((a['date'] - b['date']).days) if (a['date'] and b['date']) else 9999
                if gap <= window_days and amounts_match(a['amount_num'], b['amount_num'], tolerance):
                    union(i, j)
                    pair_gaps.append((i, j, gap))
        if not pair_gaps:
            continue

        # collect connected components that contain >= 1 matched pair
        comps = {}
        for idx in range(n):
            comps.setdefault(find(idx), []).append(entries[idx])

        for root, members in comps.items():
            if len(members) < 2:
                continue
            q = [m for m in members if m['origin'] == 'queue']
            pub = [m for m in members if m['origin'] == 'published']
            # a group is only actionable if it contains a queue item to act on
            if not q:
                continue
            # max gap among members that actually have dates
            dated = [m['date'] for m in members if m['date']]
            max_gap = (max((d2 - d1).days for d1 in dated for d2 in dated)
                       if len(dated) > 1 else 9999)
            amts = [m['amount_num'] for m in members if m['amount_num']]
            has_amount = len(amts) > 0
            tight = max_gap <= 10
            gtype = 'matches_published' if pub else 'queue_only'
            # confidence: published match + dollar amount + tight window = highest
            confidence = (
                (2.0 if pub else 0.0)
                + (1.0 if has_amount else 0.0)
                + (1.0 if tight else 0.0)
            )
            q.sort(key=lambda x: x['date'] or datetime.min)
            pub.sort(key=lambda x: x['date'] or datetime.min)
            for m in q:
                flagged_ids.add(m['id'])
            groups.append({
                'type': gtype,
                'company': members[0]['company'],
                'reason': _match_reason(members, max_gap),
                'confidence': confidence,
                'published': pub,
                'queue': q,
            })

    # highest confidence first; matches-published above queue-only at equal confidence
    groups.sort(key=lambda g: (-g['confidence'], 0 if g['type'] == 'matches_published' else 1))
    return {'groups': groups, 'flagged_ids': flagged_ids}
