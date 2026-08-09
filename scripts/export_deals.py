#!/usr/bin/env python3
"""Export deals from the master list as CSV, optionally filtered by sector.

Exists because analysis work needs the curated `company` field, and there is
no way to get it outside the app: the local turso_replica.db goes stale (it
was 480 deals while production had 628), and the published site renders the
headline in place of the company name, so scraping capitalfordefense.com
recovers company for only ~70% of rows.

Runs in GitHub Actions, which holds the Turso credentials — see
.github/workflows/export.yml. Soft-deleted duplicates are excluded.

Usage:
    python scripts/export_deals.py --out exports/deals.csv
    python scripts/export_deals.py --sectors "Electronic Warfare,Autonomous Systems/Drones"
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import get_session, MasterItem, RawItem

FIELDS = [
    "id", "company", "title", "investors", "investment_amount",
    "capital_sources", "sectors", "location", "country_hint",
    "deal_date", "source_url", "summary",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="exports/deals.csv")
    ap.add_argument("--sectors", default="",
                    help="comma-separated; a deal matches if it carries ANY of them")
    args = ap.parse_args()

    wanted = [s.strip().lower() for s in args.sectors.split(",") if s.strip()]

    session = get_session()
    try:
        rows = (
            session.query(MasterItem, RawItem)
            .outerjoin(RawItem, MasterItem.item_id == RawItem.id)
            .filter(MasterItem.removed_at.is_(None))
            .all()
        )
    finally:
        session.close()

    out = []
    for m, raw in rows:
        sectors = m.sectors or ""
        if wanted:
            have = [s.strip().lower() for s in sectors.split(",")]
            if not any(w in have for w in wanted):
                continue
        date = m.curated_at or m.published_at or (raw.published_date if raw else None)
        out.append({
            "id": m.id,
            "company": m.company or "",
            "title": m.title or "",
            "investors": m.investors or "",
            "investment_amount": m.investment_amount or "",
            "capital_sources": m.capital_sources or "",
            "sectors": sectors,
            "location": m.location or "",
            "country_hint": (m.location or "").split(",")[-1].strip(),
            "deal_date": date.strftime("%Y-%m-%d") if date else "",
            "source_url": m.source_url or (raw.canonical_url if raw else ""),
            "summary": (m.summary or "").replace("\n", " ").strip(),
        })

    out.sort(key=lambda r: r["deal_date"], reverse=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    print(f"Exported {len(out)} deals to {args.out}")
    if wanted:
        print(f"Sector filter: {args.sectors}")
    print(f"  with company:   {sum(1 for r in out if r['company'])}")
    print(f"  with investors: {sum(1 for r in out if r['investors'])}")
    print(f"  with amount:    {sum(1 for r in out if r['investment_amount'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
