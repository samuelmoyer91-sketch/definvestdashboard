#!/usr/bin/env python3
"""
Database migration: Add new AI summary fields to ai_extractions table.

Adds columns for:
- company_description
- strategic_significance
- market_implications
- summary_complete

Run this once to update your existing database.
"""

import sqlite3
from pathlib import Path

def migrate_database(db_path='databases/tracker.db'):
    """Add new columns to ai_extractions table."""

    # Resolve path
    if not Path(db_path).is_absolute():
        script_dir = Path(__file__).parent
        db_path = script_dir.parent.parent / db_path

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Migrating database: {db_path}")

    # Check which columns already exist
    cursor.execute("PRAGMA table_info(ai_extractions)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    migrations = [
        ("deal_type", "VARCHAR"),
        ("deal_amount", "VARCHAR"),
        ("investors", "TEXT"),
        ("company_description", "TEXT"),
        ("strategic_significance", "TEXT"),
        ("market_implications", "TEXT"),
        ("summary_complete", "INTEGER DEFAULT 0"),
    ]

    for column_name, column_type in migrations:
        if column_name not in existing_columns:
            try:
                sql = f"ALTER TABLE ai_extractions ADD COLUMN {column_name} {column_type}"
                cursor.execute(sql)
                print(f"  ✓ Added column: {column_name}")
            except sqlite3.OperationalError as e:
                print(f"  ⚠️  Column {column_name} may already exist: {e}")
        else:
            print(f"  ✓ Column {column_name} already exists")

    conn.commit()
    conn.close()

    print("\n✓ Migration complete!")

if __name__ == '__main__':
    migrate_database()
