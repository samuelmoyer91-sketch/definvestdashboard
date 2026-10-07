#!/usr/bin/env python3
"""Read-only: how many deals reached the triage queue per day, and what
happened to them. Counts accepts (master_list.curated_at), manual rejects and
the duplicate siblings auto-rejected on accept (rejected_items.rejected_at),
plus what is still waiting.

    gh workflow run migrate.yml -f script=triage_volume.py -f args=--days=42
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from src.database.models import get_engine

days = 42
for a in sys.argv[1:]:
    if a.startswith('--days='):
        days = int(a.split('=', 1)[1])

engine = get_engine()
with engine.connect() as c:
    since = f"date('now', '-{days} days')"
    acc = dict(c.execute(text(
        f"SELECT date(curated_at), count(*) FROM master_list "
        f"WHERE date(curated_at) >= {since} GROUP BY 1")).fetchall())
    rej = dict(c.execute(text(
        f"SELECT date(rejected_at), count(*) FROM rejected_items "
        f"WHERE date(rejected_at) >= {since} AND rejection_reason NOT LIKE 'Duplicate — %' "
        f"GROUP BY 1")).fetchall())
    auto = dict(c.execute(text(
        f"SELECT date(rejected_at), count(*) FROM rejected_items "
        f"WHERE date(rejected_at) >= {since} AND rejection_reason LIKE 'Duplicate — %' "
        f"GROUP BY 1")).fetchall())
    pending = c.execute(text(
        "SELECT count(*) FROM raw_items r JOIN ai_extractions e ON e.item_id = r.id "
        "WHERE r.status IN ('scraped', 'extraction_refused') "
        "AND r.id NOT IN (SELECT item_id FROM rejected_items) "
        "AND r.id NOT IN (SELECT item_id FROM master_list)"
    )).scalar()

print("date        accept  reject  auto-dup  total")
for d in sorted(set(acc) | set(rej) | set(auto)):
    a, r, u = acc.get(d, 0), rej.get(d, 0), auto.get(d, 0)
    print(f"{d}  {a:6}  {r:6}  {u:8}  {a + r + u:5}")
print(f"pending in queue now (approx.): {pending}")
