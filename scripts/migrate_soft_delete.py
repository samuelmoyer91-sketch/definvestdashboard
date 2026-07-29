#!/usr/bin/env python3
"""Add master_list.removed_at / removed_reason (soft-delete columns).

Why this exists as a standalone script instead of relying on the startup
migration in src/web/app.py: that migration ran on Railway and reported
success, but the columns were not present afterwards and the app 500'd with
"no such column: master_list.removed_at". DDL issued through the libsql
embedded replica did not end up on the Turso primary.

GitHub Actions talks to the same database and writes to it successfully every
day, so running the ALTER from there is the proven path. This script is
idempotent — safe to re-run, and safe to run when the columns already exist.

Usage:
    python scripts/migrate_soft_delete.py          # apply
    python scripts/migrate_soft_delete.py --check  # report only, no writes
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from src.database.models import get_engine, sync_turso

COLUMNS = [
    ("removed_at", "DATETIME"),
    ("removed_reason", "TEXT"),
]


def existing_columns(conn):
    """Column names on master_list, via PRAGMA.

    PRAGMA is used rather than the try-SELECT-except-ALTER pattern in
    app.py: a failed SELECT can leave the connection in a state where the
    follow-up ALTER behaves unpredictably, which is a prime suspect for the
    silent failure this script exists to repair.
    """
    rows = conn.execute(text("PRAGMA table_info(master_list)")).fetchall()
    return {r[1] for r in rows}


def main():
    check_only = "--check" in sys.argv
    engine = get_engine()

    with engine.connect() as conn:
        present = existing_columns(conn)
        missing = [(c, t) for c, t in COLUMNS if c not in present]

        print(f"master_list has {len(present)} columns")
        for col, _ in COLUMNS:
            print(f"  {col}: {'present' if col in present else 'MISSING'}")

        if not missing:
            print("Nothing to do.")
            return 0

        if check_only:
            print(f"--check: would add {[c for c, _ in missing]}")
            return 1

        for col, typedef in missing:
            print(f"Adding {col} {typedef}...")
            conn.execute(text(f"ALTER TABLE master_list ADD COLUMN {col} {typedef}"))
            conn.commit()

    # Push the DDL to the primary before verifying, then re-open a connection
    # so the check reads real post-sync state rather than local cache.
    sync_turso()

    engine = get_engine()
    with engine.connect() as conn:
        present = existing_columns(conn)

    still_missing = [c for c, _ in COLUMNS if c not in present]
    if still_missing:
        print(f"FAILED: {still_missing} still missing after ALTER + sync")
        return 1

    # Prove the columns are actually queryable, which is what the app does.
    with engine.connect() as conn:
        n = conn.execute(text(
            "SELECT COUNT(*) FROM master_list WHERE removed_at IS NULL"
        )).scalar()
    print(f"OK: columns present; {n} active (non-removed) deals")
    return 0


if __name__ == "__main__":
    sys.exit(main())
