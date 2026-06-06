#!/usr/bin/env python3
"""
Direct-feed verification report.

READ-ONLY. Answers the four questions that decide whether the direct-publisher
RSS feed migration is actually working — reusable every time we add a feed.

  1. Are direct-feed scrapes CLEAN? (real article text, not ~11-char stubs)
     — the core premise of the whole migration.
  2. Have any PUBLISHED deals come from direct feeds? (the payoff)
  3. Per-feed funnel health: raw -> reached-triage -> accepted / rejected.
  4. Duplicate load: how many direct-feed items are flagged as possible dups.

Direct feeds are identified by feed_source LIKE 'Direct:%'. Google feeds are
shown alongside as a baseline so "clean" / "productive" is relative.

Usage:
    python3 scripts/verify_feeds.py                 # all four checks
    python3 scripts/verify_feeds.py --since 2026-05-31   # limit to items found on/after a date
    python3 scripts/verify_feeds.py --stub-len 200      # treat clean_text <= N chars as a failed scrape (default 200)

Needs live DB access: TURSO_DATABASE_URL + TURSO_AUTH_TOKEN in env/.env, OR a
recently-synced turso_replica.db. The script reports which it used and how
fresh the data is, so a stale replica can't silently mislead.
"""

import sys
import argparse
import sqlite3
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

REPLICA = ROOT / "turso_replica.db"
STUB_LEN_DEFAULT = 200   # clean_text <= this many chars == failed/stub scrape


def get_conn():
    """Return (sqlite3 connection, source_label). Tries a live Turso sync first
    (if creds present), else falls back to the local replica as-is."""
    import os
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except Exception:
        pass
    url = os.getenv("TURSO_DATABASE_URL")
    tok = os.getenv("TURSO_AUTH_TOKEN")
    if url and tok:
        try:
            import libsql_experimental as libsql
            conn = libsql.connect(str(REPLICA), sync_url=url, auth_token=tok)
            conn.sync()
            return sqlite3.connect(str(REPLICA)), "live Turso (synced just now)"
        except Exception as e:
            print(f"  ! Turso sync failed ({e}); falling back to local replica.\n")
    if not REPLICA.exists():
        print("ERROR: no Turso creds and no local replica. Set TURSO_DATABASE_URL "
              "+ TURSO_AUTH_TOKEN (in .env) or sync the replica first.")
        sys.exit(1)
    return sqlite3.connect(str(REPLICA)), "local replica (may be STALE)"


def main():
    ap = argparse.ArgumentParser(description="Read-only direct-feed verification report.")
    ap.add_argument("--since", default=None, help="Only items with date_found >= this (YYYY-MM-DD)")
    ap.add_argument("--stub-len", type=int, default=STUB_LEN_DEFAULT,
                    help=f"clean_text <= N chars counts as a failed/stub scrape (default {STUB_LEN_DEFAULT})")
    args = ap.parse_args()

    conn, source = get_conn()
    cur = conn.cursor()

    where_since = ""
    params = []
    if args.since:
        where_since = " AND r.date_found >= ?"
        params = [args.since]

    print("=" * 78)
    print("DIRECT-FEED VERIFICATION REPORT")
    print(f"Data source: {source}")
    freshest = cur.execute("SELECT MAX(date_found) FROM raw_items").fetchone()[0]
    print(f"Most recent raw_item: {freshest}")
    if args.since:
        print(f"Filtered to items found on/after {args.since}")
    print("=" * 78)

    # ---- Q1: clean scrapes -------------------------------------------------
    print("\n[1] SCRAPE CLEANLINESS  (the core premise — direct URLs should scrape clean)")
    print(f"    'stub/failed' = scrape_success=0 OR clean_text length <= {args.stub_len}\n")
    rows = cur.execute(f"""
        SELECT
          CASE WHEN r.feed_source LIKE 'Direct:%' THEN 'DIRECT' ELSE 'google' END AS kind,
          COUNT(*) AS scraped,
          SUM(CASE WHEN ac.scrape_success=1 AND LENGTH(COALESCE(ac.clean_text,'')) > ? THEN 1 ELSE 0 END) AS clean,
          SUM(CASE WHEN ac.scrape_success=0 OR LENGTH(COALESCE(ac.clean_text,'')) <= ? THEN 1 ELSE 0 END) AS stub,
          CAST(AVG(LENGTH(COALESCE(ac.clean_text,''))) AS INT) AS avg_len
        FROM article_content ac JOIN raw_items r ON r.id = ac.item_id
        WHERE 1=1 {where_since}
        GROUP BY kind ORDER BY kind
    """, [args.stub_len, args.stub_len] + params).fetchall()
    print(f"    {'group':8} {'scraped':>8} {'clean':>7} {'stub':>6} {'clean%':>7} {'avg_chars':>10}")
    for r in rows:
        pct = f"{100*r[2]/r[1]:.0f}%" if r[1] else "-"
        print(f"    {r[0]:8} {r[1]:>8} {r[2]:>7} {r[3]:>6} {pct:>7} {r[4] or 0:>10}")

    print("\n    Per direct feed:")
    rows = cur.execute(f"""
        SELECT r.feed_source,
          COUNT(*) AS scraped,
          SUM(CASE WHEN ac.scrape_success=1 AND LENGTH(COALESCE(ac.clean_text,'')) > ? THEN 1 ELSE 0 END) AS clean,
          CAST(AVG(LENGTH(COALESCE(ac.clean_text,''))) AS INT) AS avg_len
        FROM article_content ac JOIN raw_items r ON r.id = ac.item_id
        WHERE r.feed_source LIKE 'Direct:%' {where_since}
        GROUP BY r.feed_source ORDER BY scraped DESC
    """, [args.stub_len] + params).fetchall()
    if not rows:
        print("      (no scraped direct-feed items yet)")
    for r in rows:
        pct = f"{100*r[2]/r[1]:.0f}%" if r[1] else "-"
        print(f"      {r[0][:40]:40} scraped={r[1]:>3} clean={pct:>4} avg={r[3] or 0:>6} chars")

    # ---- Q2: published deals from direct feeds ----------------------------
    print("\n[2] PUBLISHED DEALS BY FEED SOURCE  (the payoff — are direct feeds producing accepted deals?)")
    rows = cur.execute(f"""
        SELECT r.feed_source, COUNT(*) AS accepted
        FROM master_list m JOIN raw_items r ON r.id = m.item_id
        WHERE 1=1 {where_since}
        GROUP BY r.feed_source ORDER BY accepted DESC
    """, params).fetchall()
    direct_pub = sum(r[1] for r in rows if (r[0] or '').startswith('Direct:'))
    total_pub = sum(r[1] for r in rows)
    print(f"    Direct-feed published deals: {direct_pub} of {total_pub} total"
          + (f" ({100*direct_pub/total_pub:.0f}%)" if total_pub else ""))
    for r in rows:
        mark = '>>' if (r[0] or '').startswith('Direct:') else '  '
        print(f"    {mark} {(r[0] or '(none)')[:42]:42} {r[1]:>4}")

    # ---- Q3: per-feed funnel ---------------------------------------------
    print("\n[3] PER-FEED FUNNEL  (raw -> reached scrape -> accepted / rejected)")
    rows = cur.execute(f"""
        SELECT r.feed_source,
          COUNT(*) AS raw,
          SUM(CASE WHEN r.status='auto_rejected' THEN 1 ELSE 0 END) AS autorej,
          SUM(CASE WHEN r.status='ai_screened_out' THEN 1 ELSE 0 END) AS screened,
          SUM(CASE WHEN EXISTS(SELECT 1 FROM master_list m WHERE m.item_id=r.id) THEN 1 ELSE 0 END) AS accepted,
          SUM(CASE WHEN EXISTS(SELECT 1 FROM rejected_items ri WHERE ri.item_id=r.id) THEN 1 ELSE 0 END) AS rejected
        FROM raw_items r
        WHERE r.feed_source LIKE 'Direct:%' {where_since}
        GROUP BY r.feed_source ORDER BY raw DESC
    """, params).fetchall()
    print(f"    {'feed':40} {'raw':>5} {'autorej':>8} {'screen':>7} {'accept':>7} {'reject':>7}")
    for r in rows:
        print(f"    {r[0][:40]:40} {r[1]:>5} {r[2]:>8} {r[3]:>7} {r[4]:>7} {r[5]:>7}")
    if not rows:
        print("      (no direct-feed raw items in range)")

    # ---- Q4: duplicate load ---------------------------------------------
    print("\n[4] DUPLICATE LOAD  (direct-feed items rejected as duplicates)")
    rows = cur.execute(f"""
        SELECT
          CASE WHEN r.feed_source LIKE 'Direct:%' THEN 'DIRECT' ELSE 'google' END AS kind,
          COUNT(*) AS dup_rejects
        FROM rejected_items ri JOIN raw_items r ON r.id = ri.item_id
        WHERE LOWER(COALESCE(ri.rejection_reason,'')) LIKE '%duplicate%' {where_since}
        GROUP BY kind ORDER BY kind
    """, params).fetchall()
    for r in rows:
        print(f"    {r[0]:8} duplicate-rejections: {r[1]}")
    if not rows:
        print("    (no duplicate-tagged rejections in range — note: dups caught at ingest")
        print("     via exact-URL show as 'skipped duplicates' in logs, not rejected_items)")

    print("\n" + "-" * 78)
    print("Read: [1] is the gate — if DIRECT clean% is high and avg_chars is in the")
    print("thousands, the migration premise holds. [2] shows business payoff. [3]/[4]")
    print("inform whether to enable Pulse 2.0 and which Google feeds to retire.")
    conn.close()


if __name__ == "__main__":
    main()
