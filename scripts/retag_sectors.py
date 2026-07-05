#!/usr/bin/env python3
"""
Backfill sector tags on existing master_list deals for the expanded taxonomy.

Keyword-matches each deal's title + summary + company + investors against the
9 new categories and ADDS any matches (never removes an existing tag). Also
normalizes the handful of rogue free-text tags to canonical values.

DRY-RUN BY DEFAULT — prints a per-category proposal + writes a full review
file. Nothing is written to the database unless you pass --apply.

Usage:
    python3 scripts/retag_sectors.py                 # dry run: preview + write review CSV
    python3 scripts/retag_sectors.py --only Maritime/Naval,Quantum   # preview specific tags
    python3 scripts/retag_sectors.py --apply         # WRITE additions to the live DB
    python3 scripts/retag_sectors.py --apply --only Maritime/Naval   # apply just some

Needs live DB access (TURSO_DATABASE_URL + TURSO_AUTH_TOKEN in env/.env).
Additive + reversible-ish: a review CSV of every change is written each run.
"""

import sys
import re
import csv
import argparse
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

# Canonical display order for re-emitting the sectors string
CANON_ORDER = [
    'Autonomous Systems/Drones', 'AI/ML', 'Quantum', 'Software/IT', 'Cybersecurity',
    'Communications', 'Sensors/ISR', 'Electronic Warfare', 'Space/Satellites', 'Aerospace',
    'Propulsion/Engines', 'Maritime/Naval', 'Ground Vehicles', 'Munitions/Weapons',
    'Semiconductors/Electronics', 'Advanced Materials', 'Critical Minerals', 'Energy/Power',
    'Manufacturing/Production', 'Logistics/Sustainment', 'Biotech/Medical', 'Other',
]
_ORDER = {t: i for i, t in enumerate(CANON_ORDER)}

# --- Rogue free-text tags -> canonical (applied to existing tags) --------
ROGUE_MAP = {
    'ai': 'AI/ML',
    'materials': 'Advanced Materials',
    'mineral refining': 'Critical Minerals',
    'intelligence': 'Sensors/ISR',   # single deal; ISR is the best-fit bucket
}

# --- Keyword patterns for the NEW categories only ------------------------
# Only the 9 additions are matched; existing tags are left as curated. Patterns
# are conservative — avoid traps like "think tank" (no bare 'tank'), "energetics"
# (that's munitions, not Energy), "data mining" (kept out of Critical Minerals).
NEW_PATTERNS = {
    'Maritime/Naval': r'\b(maritime|naval|navy|shipyard|shipbuild\w*|submarine|vessel|undersea|underwater|sonar|dockyard|uuv|usv|surface combatant|frigate|destroyer|corvette|amphibious|littoral)\b|\bships?\b|\bboats?\b',
    'Propulsion/Engines': r'\b(propulsion|rocket motor|solid rocket|jet engine|scramjet|ramjet|turbofan|turboprop|turbine)\b|\bengines?\b',
    'Sensors/ISR': r'\b(sensors?|radar|lidar|electro.?optical|infrared|seeker|surveillance|reconnaissance|isr|sigint|geoint|elint|hyperspectral|imaging payload)\b',
    'Energy/Power': r'\b(nuclear|reactor|smr|small modular reactor|batter(y|ies)|energy storage|microgrid|fuel cell|power generation|photovoltaic|grid resilience)\b',
    'Critical Minerals': r'\b(rare[- ]earth|critical mineral|permanent magnets?|\bmagnets?\b|lithium|titanium sponge|tungsten|antimony|graphite|gallium|germanium|mineral refin\w*)\b',
    'Ground Vehicles': r'\b(armou?red vehicle|combat vehicle|tactical vehicle|infantry fighting vehicle|ifv|main battle tank|howitzer|self-propelled|troop carrier|mine-resistant|mrap|ground vehicle)\b',
    'Quantum': r'\bquantum\b',
    'Logistics/Sustainment': r'\b(logistics|sustainment|mro|maintenance,? repair|overhaul|depot)\b',
    'Biotech/Medical': r'\b(biotech\w*|biomanufactur\w*|pharmaceutical|pharma|medical|life support|biosciences|vaccine)\b',
}
NEW_RE = {tag: re.compile(pat, re.I) for tag, pat in NEW_PATTERNS.items()}


def normalize_existing(tags):
    """Map rogue free-text tags to canonical; drop empties/dupes. Returns (list, changed)."""
    out, changed = [], False
    for t in tags:
        key = t.strip().lower()
        if key in ROGUE_MAP:
            canon = ROGUE_MAP[key]
            if canon != t.strip():
                changed = True
            out.append(canon)
        elif t.strip():
            out.append(t.strip())
    # de-dupe preserving first occurrence
    seen, deduped = set(), []
    for t in out:
        if t not in seen:
            seen.add(t); deduped.append(t)
    if len(deduped) != len(out):
        changed = True
    return deduped, changed


def suggest_additions(text, existing, only=None):
    """Return the set of NEW-category tags to add based on text, minus any already present."""
    have = set(existing)
    adds = set()
    for tag, rx in NEW_RE.items():
        if only and tag not in only:
            continue
        if tag not in have and rx.search(text):
            adds.add(tag)
    return adds


def canon_sort(tags):
    return sorted(tags, key=lambda t: _ORDER.get(t, 999))


def main():
    ap = argparse.ArgumentParser(description='Backfill sector tags (dry-run default).')
    ap.add_argument('--apply', action='store_true', help='WRITE changes to the DB (default: dry run)')
    ap.add_argument('--only', default=None, help='Comma-separated subset of NEW tags to apply')
    args = ap.parse_args()
    only = set(s.strip() for s in args.only.split(',')) if args.only else None
    if only:
        bad = only - set(NEW_PATTERNS)
        if bad:
            print(f"Unknown --only tags: {bad}\nValid: {list(NEW_PATTERNS)}"); sys.exit(1)

    # Connect directly via libsql (embedded replica → write-through to the live
    # primary). Raw SQL on only the columns we need avoids ORM schema-drift
    # issues (the replica's master_list can lag the model's columns).
    import os
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env')
    except Exception:
        pass
    url = os.environ.get('TURSO_DATABASE_URL')
    token = os.environ.get('TURSO_AUTH_TOKEN')
    if not (url and token):
        print("ERROR: TURSO_DATABASE_URL + TURSO_AUTH_TOKEN required (in .env)."); sys.exit(1)
    try:
        import libsql
    except ImportError:
        import libsql_experimental as libsql
    conn = libsql.connect(str(ROOT / 'turso_replica.db'), sync_url=url, auth_token=token)
    conn.sync()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, company, title, summary, investors, sectors FROM master_list"
    ).fetchall()

    from collections import Counter, defaultdict
    add_counts = Counter()
    norm_count = 0
    samples = defaultdict(list)
    changes = []   # (id, company, old, new)

    for rid, company, title, summary, investors, sectors in rows:
        existing = [t for t in (sectors or '').split(',') if t.strip()]
        normalized, norm_changed = normalize_existing(existing)
        text = ' '.join(filter(None, [title, company, summary, investors]))
        adds = suggest_additions(text, normalized, only)

        if not adds and not norm_changed:
            continue
        new_tags = canon_sort(list(dict.fromkeys(normalized + list(adds))))
        new_str = ','.join(new_tags)
        if new_str == (sectors or ''):
            continue
        for t in adds:
            add_counts[t] += 1
            if len(samples[t]) < 6:
                samples[t].append(title or company or f'#{rid}')
        if norm_changed:
            norm_count += 1
        changes.append((rid, company or '', sectors or '', new_str))
        if args.apply:
            cur.execute("UPDATE master_list SET sectors = ? WHERE id = ?", (new_str, rid))

    print('=' * 74)
    print(f"SECTOR RETAG {'(APPLYING)' if args.apply else '(DRY RUN — no writes)'}"
          + (f"  [only: {', '.join(sorted(only))}]" if only else ''))
    print(f"{len(rows)} deals scanned | {len(changes)} would change | "
          f"{norm_count} rogue-tag normalizations")
    print('=' * 74)
    print("\nADDITIONS BY NEW CATEGORY:")
    for tag in CANON_ORDER:
        if add_counts.get(tag):
            print(f"\n  + {tag}  ({add_counts[tag]} deals)")
            for s in samples[tag]:
                print(f"      - {s[:72]}")

    # write review file
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    review = ROOT / f'sector_retag_review_{stamp}.csv'
    with open(review, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['master_id', 'company', 'old_sectors', 'new_sectors'])
        w.writerows(changes)
    print(f"\nFull change list written to: {review.name}")

    if args.apply:
        conn.commit()
        try:
            conn.sync()
        except Exception:
            pass
        print(f"\n✓ APPLIED {len(changes)} changes to the live database.")
    else:
        print("\nDry run only — nothing written to the DB. Re-run with --apply to commit.")


if __name__ == '__main__':
    main()
