#!/usr/bin/env python3
"""
Database migration: Add new category fields to ai_extractions table.

This migration adds the same enhanced category fields to AI extractions
that were added to the master_list table.
"""

import sqlite3
from pathlib import Path

def migrate_database(db_path='databases/tracker.db'):
    """Add new category columns to ai_extractions table."""

    # Resolve path
    if not Path(db_path).is_absolute():
        script_dir = Path(__file__).parent
        db_path = script_dir.parent.parent / db_path

    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check which columns already exist
    cursor.execute("PRAGMA table_info(ai_extractions)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    migrations_applied = []

    # Add transaction_type column (single-select)
    if 'transaction_type' not in existing_columns:
        cursor.execute("""
            ALTER TABLE ai_extractions
            ADD COLUMN transaction_type TEXT
        """)
        migrations_applied.append('transaction_type')
        print("  ✓ Added transaction_type column")
    else:
        print("  ⊘ transaction_type column already exists")

    # Add capital_sources column (multi-select, comma-separated)
    if 'capital_sources' not in existing_columns:
        cursor.execute("""
            ALTER TABLE ai_extractions
            ADD COLUMN capital_sources TEXT
        """)
        migrations_applied.append('capital_sources')
        print("  ✓ Added capital_sources column")
    else:
        print("  ⊘ capital_sources column already exists")

    # Add sectors column (multi-select, comma-separated)
    if 'sectors' not in existing_columns:
        cursor.execute("""
            ALTER TABLE ai_extractions
            ADD COLUMN sectors TEXT
        """)
        migrations_applied.append('sectors')
        print("  ✓ Added sectors column")
    else:
        print("  ⊘ sectors column already exists")

    conn.commit()
    conn.close()

    if migrations_applied:
        print(f"\n✅ Migration complete! Added {len(migrations_applied)} new columns")
        print("   Future AI extractions will populate these fields")
    else:
        print("\n✅ Database already up to date")

if __name__ == '__main__':
    migrate_database()
