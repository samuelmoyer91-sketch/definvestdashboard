#!/usr/bin/env python3
"""Add raw_items.split_instruction / split_parent_id (roundup splitting).

A roundup article announces several deals but produces one card that mooshes
them together. The fix is to re-extract the article once per deal, each pass
told which deal to focus on. Each pass is its own raw_items row, so every
existing UNIQUE constraint stays intact and nothing needs a table rebuild.

  split_instruction — which deal THIS pass should extract. Persisted rather
    than passed at call time because generate_ai_summaries retries anything
    with summary_complete = False; a retry without the focus would silently
    overwrite a focused extraction with a mooshed one.
  split_parent_id   — the original row a pass came from; NULL on the original.

Run this from GitHub Actions, not from the app. The startup migration in
src/web/app.py once reported success while leaving columns missing — DDL
issued through the libsql embedded replica did not reach the Turso primary.
Actions writes to the same database successfully every day, so it is the
proven path. Idempotent: safe to re-run, safe when the columns already exist.

Usage:
    gh workflow run migrate.yml -f script=migrate_split_instruction.py -f args=--check
    gh workflow run migrate.yml -f script=migrate_split_instruction.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from src.database.models import get_engine, sync_turso

TABLE = "raw_items"
COLUMNS = [
    ("split_instruction", "TEXT"),
    # No REFERENCES clause: SQLite cannot add a foreign key with ADD COLUMN
    # unless the default is NULL, and the constraint buys nothing here — the
    # column is only ever read through RawItem.split_group_id.
    ("split_parent_id", "INTEGER"),
]


def existing_columns(conn):
    """Column names on raw_items, via PRAGMA.

    PRAGMA rather than try-SELECT-except-ALTER: a failed SELECT can leave the
    connection in a state where the follow-up ALTER behaves unpredictably,
    which is the prime suspect for the silent failure noted above.
    """
    rows = conn.execute(text(f"PRAGMA table_info({TABLE})")).fetchall()
    return {r[1] for r in rows}


def main():
    check_only = "--check" in sys.argv
    engine = get_engine()

    with engine.connect() as conn:
        present = existing_columns(conn)
        missing = [(c, t) for c, t in COLUMNS if c not in present]

        print(f"{TABLE} has {len(present)} columns")
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
            conn.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN {col} {typedef}"))
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

    # Prove the columns are queryable the way the app will use them. Every
    # existing row must read as an unsplit original.
    with engine.connect() as conn:
        total = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar()
        splits = conn.execute(text(
            f"SELECT COUNT(*) FROM {TABLE} WHERE split_parent_id IS NOT NULL"
        )).scalar()
        focused = conn.execute(text(
            f"SELECT COUNT(*) FROM {TABLE} WHERE split_instruction IS NOT NULL"
        )).scalar()

    print(f"OK: columns present; {total} rows, {splits} split passes, "
          f"{focused} with a focus")
    if splits or focused:
        print("NOTE: expected 0/0 on first run — non-zero means this already ran.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
