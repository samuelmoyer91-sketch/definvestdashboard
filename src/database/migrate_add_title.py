#!/usr/bin/env python3
"""
Database migration: Add title column to master_list table.

Allows overriding the RSS-sourced title with a human-edited version.
"""

import sqlite3
from pathlib import Path


def migrate_database(db_path='databases/tracker.db'):
    """Add title column to master_list table."""

    # Resolve path
    if not Path(db_path).is_absolute():
        script_dir = Path(__file__).parent
        db_path = script_dir.parent.parent / db_path

    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check which columns already exist
    cursor.execute("PRAGMA table_info(master_list)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    if 'title' not in existing_columns:
        cursor.execute("ALTER TABLE master_list ADD COLUMN title TEXT")
        conn.commit()
        print("  ✓ Added title column to master_list")
    else:
        print("  ⊘ title column already exists")

    conn.close()
    print("\n✅ Migration complete")


if __name__ == '__main__':
    migrate_database()
