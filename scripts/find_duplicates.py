#!/usr/bin/env python3
"""
Duplicate-deal report for the master list (command-line version).

READ-ONLY. Never writes to the database, never touches the
ingest/triage/publish pipeline, never deletes anything. It reads
master_list, groups deals that look like the same underlying event, and
prints a report. You decide what to merge/remove via the edit UI.

The same report is available in the triage app at /duplicates — that's the
one built into your normal workflow. This CLI version is for ad-hoc runs.

The matching logic and tuning knobs (WINDOW_DAYS, AMOUNT_TOLERANCE,
NAME_NOISE) live in src/utils/dedup.py and are shared with the web page —
change them there once and both reflect it.

Usage:
    python3 scripts/find_duplicates.py                # default report
    python3 scripts/find_duplicates.py --days 45      # wider time window
    python3 scripts/find_duplicates.py --published    # only published deals
    python3 scripts/find_duplicates.py --all-clusters # also show "probably distinct" groups
"""

import sys
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.database.models import get_session, MasterItem
from src.utils import dedup


def _print_cluster(cluster, mark_flagged=True):
    entries = cluster['entries']
    flagged = cluster['flagged_ids']
    for d in entries:
        ds = d['date'].strftime('%Y-%m-%d') if d['date'] else '????-??-??'
        mark = '>>' if (mark_flagged and d['id'] in flagged) else '  '
        print(f'  {mark} id={d["id"]:>4} | {ds} | {dedup.fmt_amount(d["amount_num"]):>8} | {d["title"][:58]}')


def main():
    ap = argparse.ArgumentParser(description='Read-only duplicate-deal report.')
    ap.add_argument('--days', type=int, default=dedup.WINDOW_DAYS,
                    help=f'Time window in days (default {dedup.WINDOW_DAYS})')
    ap.add_argument('--published', action='store_true', help='Only published deals')
    ap.add_argument('--all-clusters', action='store_true',
                    help='Also list multi-card companies that look like DISTINCT deals')
    args = ap.parse_args()

    session = get_session()
    q = session.query(MasterItem)
    if args.published:
        q = q.filter(MasterItem.published == True)  # noqa: E712
    rows = q.all()

    deals = [{
        'id': r.id,
        'company': r.company or r.title,
        'amount': r.investment_amount,
        'date': r.curated_at or r.published_at,
        'title': r.title or r.company,
        'source': r.source_url,
    } for r in rows]

    result = dedup.find_clusters(deals, window_days=args.days)

    print('=' * 78)
    print(f'DUPLICATE-DEAL REPORT  (window={args.days}d, amount tolerance={dedup.AMOUNT_TOLERANCE:.0%})')
    print(f'{len(deals)} deals scanned | {len(result["likely"])} likely-duplicate clusters | '
          f'{len(result["distinct"])} multi-card companies look distinct')
    print('=' * 78)

    for cluster in result['likely']:
        print(f'\n⚠  {cluster["company"]}  —  {len(cluster["entries"])} cards, {len(cluster["pairs"])} matching pair(s)')
        _print_cluster(cluster)
        if len(cluster['entries']) > len(cluster['flagged_ids']):
            print('     (cards without ">>" share the company name but were not matched as dups)')

    print('\n' + '-' * 78)
    print(f'Estimated double-counted capital across likely-dup pairs: {dedup.fmt_amount(result["overcount"])}')
    print('(Rough — assumes each matching pair double-counts the smaller amount.)')

    if args.all_clusters and result['distinct']:
        print('\n' + '=' * 78)
        print('MULTI-CARD COMPANIES THAT LOOK LIKE DISTINCT DEALS (review, not flagged)')
        print('=' * 78)
        for cluster in result['distinct']:
            print(f'\nℹ  {cluster["company"]}  —  {len(cluster["entries"])} cards')
            _print_cluster(cluster, mark_flagged=False)

    print('\nNothing was changed. Use the edit UI to merge/remove any confirmed duplicates.')
    session.close()


if __name__ == '__main__':
    main()
