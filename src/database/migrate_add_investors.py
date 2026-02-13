#!/usr/bin/env python3
"""
Database migration: Create investors and deal_investors tables.

Sets up the normalized investor tracking system.
"""

import sqlite3
from pathlib import Path


def migrate_database(db_path='databases/tracker.db'):
    """Create investors and deal_investors tables."""

    # Resolve path
    if not Path(db_path).is_absolute():
        script_dir = Path(__file__).parent
        db_path = script_dir.parent.parent / db_path

    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if tables already exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='investors'")
    investors_exists = cursor.fetchone() is not None

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='deal_investors'")
    deal_investors_exists = cursor.fetchone() is not None

    if not investors_exists:
        cursor.execute("""
            CREATE TABLE investors (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                deal_count INTEGER DEFAULT 0,
                first_seen DATETIME,
                last_seen DATETIME
            )
        """)
        cursor.execute("CREATE INDEX ix_investors_name ON investors (name)")
        cursor.execute("CREATE INDEX ix_investors_slug ON investors (slug)")
        print("  ✓ Created investors table")
    else:
        print("  ⊘ investors table already exists")

    if not deal_investors_exists:
        cursor.execute("""
            CREATE TABLE deal_investors (
                id INTEGER PRIMARY KEY,
                master_item_id INTEGER NOT NULL REFERENCES master_list(id),
                investor_id INTEGER NOT NULL REFERENCES investors(id),
                is_lead BOOLEAN DEFAULT 0
            )
        """)
        print("  ✓ Created deal_investors table")
    else:
        print("  ⊘ deal_investors table already exists")

    conn.commit()
    conn.close()
    print("\n✅ Migration complete")


if __name__ == '__main__':
    migrate_database()
