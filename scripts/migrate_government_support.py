#!/usr/bin/env python3
"""
One-time migration: rename 'Government/Contract' → 'Government Support'
in capital_sources and capital_type columns of master_items table.

Run from the project root:
    python scripts/migrate_government_support.py
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.models import get_session, sync_turso, MasterItem


def migrate():
    session = get_session()
    try:
        items = session.query(MasterItem).all()
        updated = 0

        for item in items:
            changed = False

            # capital_sources column
            if item.capital_sources and 'Government/Contract' in item.capital_sources:
                item.capital_sources = item.capital_sources.replace(
                    'Government/Contract', 'Government Support'
                )
                changed = True

            # capital_type column (legacy fallback)
            if hasattr(item, 'capital_type') and item.capital_type and 'Government/Contract' in item.capital_type:
                item.capital_type = item.capital_type.replace(
                    'Government/Contract', 'Government Support'
                )
                changed = True

            if changed:
                updated += 1

        session.commit()
        sync_turso()
        print(f"✓ Migration complete: updated {updated} item(s), synced to Turso")

    except Exception as e:
        session.rollback()
        print(f"✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == '__main__':
    migrate()
