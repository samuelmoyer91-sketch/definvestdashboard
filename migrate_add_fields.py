"""Migration script to add investors and deal_type columns to master_list table."""

import sqlite3
from pathlib import Path

def migrate():
    db_path = Path(__file__).parent / "data" / "tracker.db"

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(master_list)")
    columns = [row[1] for row in cursor.fetchall()]

    migrations_needed = []

    if 'investors' not in columns:
        migrations_needed.append("ALTER TABLE master_list ADD COLUMN investors VARCHAR")

    if 'deal_type' not in columns:
        migrations_needed.append("ALTER TABLE master_list ADD COLUMN deal_type VARCHAR")

    if not migrations_needed:
        print("✓ Database already up to date - no migrations needed")
        conn.close()
        return

    # Apply migrations
    for migration in migrations_needed:
        print(f"Applying: {migration}")
        cursor.execute(migration)

    conn.commit()
    conn.close()

    print(f"✓ Successfully added {len(migrations_needed)} column(s) to master_list table")

if __name__ == "__main__":
    migrate()
