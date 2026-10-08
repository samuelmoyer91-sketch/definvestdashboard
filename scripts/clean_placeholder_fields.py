#!/usr/bin/env python3
"""Clean placeholders and notes out of accepted deals (2026-10-07).

Before the field_hygiene clean-up existed, whatever the AI wrote was saved on
accept. This applies the same rules to deals already accepted:
  - summaries: drop notes about the article ("...not detailed in available
    content.", "Unknown - article content not accessible due to paywall")
  - investors: drop "Unknown" and unnamed groups ("Institutional investors",
    "Existing shareholders"), keep names inside them, and rebuild that deal's
    investor links with the current parser
  - then delete investor records that are placeholders or unnamed groups and
    no longer have any deals ("Unknown" had 13)

Dry run by default. Runs in Actions via migrate.yml:
    script: clean_placeholder_fields.py   args: (none)      -> preview
    script: clean_placeholder_fields.py   args: --apply     -> write
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_session, sync_turso, Investor, DealInvestor, MasterItem
from src.utils.field_hygiene import (clean_investor_text, strip_source_notes,
                                     is_placeholder, is_unnamed_group)
from src.utils.investor_parser import parse_investors, slugify

_GROUP_TAIL = re.compile(r'\s+(?:and|&|plus|with|alongside)\s+(?:[\w.\'’-]+\s+){0,4}?'
                         r'(?:investors|backers|shareholders|lenders|family\s+offices)\b', re.I)


def investors_need_cleaning(text):
    """Rewrite a list's text only when part of it is a placeholder or names no
    one ("Unknown", "and angel investors", "plus state-linked investors").
    Lists that are merely wordy ("Led by X with participation from Y") keep
    their wording; only their investor records are rebuilt."""
    if text is None:
        return False
    if is_placeholder(text):
        return True
    for p in re.split(r'[,;]', text):
        p = re.sub(r'^(?:and|plus|with|also)\s+', '', p.strip(), flags=re.I)
        if is_placeholder(p) or is_unnamed_group(p) or _GROUP_TAIL.search(p):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='without this, report only')
    args = ap.parse_args()

    from src.web.app import _sync_investor_links  # app import sets up paths/templates

    session = get_session()
    try:
        deals = session.query(MasterItem).order_by(MasterItem.id).all()
        summary_changes, investor_changes = [], []
        for m in deals:
            new_summary = strip_source_notes(m.summary)
            if (new_summary or '') != (m.summary or '') and m.summary is not None:
                summary_changes.append((m, new_summary))
            if investors_need_cleaning(m.investors):
                new_inv = clean_investor_text(m.investors)
                if (new_inv or '') != (m.investors or ''):
                    investor_changes.append((m, new_inv))

        verb = 'FIX  ' if args.apply else 'WOULD'
        print(f"Summaries with notes about the article: {len(summary_changes)}")
        for m, new in summary_changes:
            print(f"  {verb} #{m.id}: {m.summary!r}\n            -> {new!r}")
        print(f"\nInvestor lists with placeholders or unnamed groups: {len(investor_changes)}")
        for m, new in investor_changes:
            print(f"  {verb} #{m.id}: {m.investors!r} -> {new!r}")

        # Investor records: rebuild the deals linked to a placeholder or
        # unnamed-group record, or whose text was just rewritten. (Not every
        # deal whose records differ from the parser: that would also touch
        # deals with no records and re-create the parked "Inc." splits.)
        new_text = {m.id: new for m, new in investor_changes}
        junk_slugs = {inv.slug for inv in session.query(Investor).all()
                      if is_placeholder(inv.name) or is_unnamed_group(inv.name)}
        linked = {}
        for link, inv in session.query(DealInvestor, Investor).join(
                Investor, DealInvestor.investor_id == Investor.id).all():
            linked.setdefault(link.master_item_id, set()).add(inv.slug)
        rebuild = []
        for m in deals:
            have = linked.get(m.id, set())
            if m.id not in new_text and not (have & junk_slugs):
                continue
            text = new_text.get(m.id, m.investors)
            want = {slugify(n) for n, _ in parse_investors(text)} if text else set()
            if want != have:
                rebuild.append((m, sorted(have - want), sorted(want - have)))
        print(f"\nDeals whose investor records change: {len(rebuild)}")
        for m, gone, added in rebuild:
            print(f"  {verb} #{m.id}: drop {gone}  add {added}")

        if args.apply:
            for m, new in summary_changes:
                m.summary = new
            for m, new in investor_changes:
                m.investors = new
            for m, _, _ in rebuild:
                _sync_investor_links(session, m)
            session.commit()

        # Investor records that are placeholders or unnamed groups.
        junk = [inv for inv in session.query(Investor).all()
                if is_placeholder(inv.name) or is_unnamed_group(inv.name)]
        print(f"\nPlaceholder / unnamed-group investor records: {len(junk)}")
        removed = 0
        for inv in junk:
            links = session.query(DealInvestor).filter_by(investor_id=inv.id).count()
            if links == 0:
                print(f"  {'DELETE' if args.apply else 'WOULD DELETE'} {inv.name!r} (no deals left)")
                if args.apply:
                    session.delete(inv)
                removed += 1
            else:
                print(f"  KEEP  {inv.name!r}: still linked to {links} deal(s)"
                      f"{'' if args.apply else ' (expected before --apply)'}")
        if args.apply:
            session.commit()
            sync_turso()

        print(f"\n{'applied' if args.apply else 'would apply'}: {len(summary_changes)} summaries, "
              f"{len(investor_changes)} investor lists rewritten, {len(rebuild)} deals' investor "
              f"records rebuilt, {removed} investor records removed")
    finally:
        session.close()


if __name__ == '__main__':
    main()
