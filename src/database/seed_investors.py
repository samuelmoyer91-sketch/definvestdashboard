#!/usr/bin/env python3
"""
Seed script: Parse existing MasterItem.investors text and populate investor tables.

Run this AFTER migrate_add_investors.py to backfill data from existing deals.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.investor_parser import parse_investors, slugify


def seed_investors(db_path='databases/tracker.db'):
    """Parse all existing MasterItem.investors text and create Investor + DealInvestor records."""

    # Resolve path
    if not Path(db_path).is_absolute():
        script_dir = Path(__file__).parent
        db_path = script_dir.parent.parent / db_path

    # Use raw sqlite3 to avoid SQLAlchemy schema cache issues
    # (the title column was added via raw SQL migration, ORM may not see it yet)
    from src.database.models import get_session, Investor, DealInvestor

    session = get_session()
    try:
        # Use raw SQL to get master items with investor data
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, investors, curated_at FROM master_list WHERE investors IS NOT NULL AND investors != ''")
        rows = cursor.fetchall()
        conn.close()

        master_items = [dict(row) for row in rows]

        print(f"Found {len(master_items)} deals with investor data")

        investors_created = 0
        links_created = 0

        for row in master_items:
            parsed = parse_investors(row['investors'])
            if not parsed:
                continue

            curated_at = datetime.utcnow()
            if row['curated_at']:
                try:
                    curated_at = datetime.fromisoformat(row['curated_at'])
                except (ValueError, TypeError):
                    pass

            for name, is_lead in parsed:
                slug = slugify(name)

                # Get or create investor
                investor = session.query(Investor).filter_by(slug=slug).first()
                if not investor:
                    investor = Investor(
                        name=name,
                        slug=slug,
                        deal_count=0,
                        first_seen=curated_at,
                        last_seen=curated_at,
                    )
                    session.add(investor)
                    session.flush()  # Get the ID
                    investors_created += 1

                # Update last_seen if this deal is newer
                if curated_at and (not investor.last_seen or curated_at > investor.last_seen):
                    investor.last_seen = curated_at

                # Check if link already exists
                existing_link = session.query(DealInvestor).filter_by(
                    master_item_id=row['id'],
                    investor_id=investor.id
                ).first()

                if not existing_link:
                    link = DealInvestor(
                        master_item_id=row['id'],
                        investor_id=investor.id,
                        is_lead=is_lead,
                    )
                    session.add(link)
                    links_created += 1

        # Update deal counts
        for investor in session.query(Investor).all():
            investor.deal_count = session.query(DealInvestor).filter_by(
                investor_id=investor.id
            ).count()

        session.commit()

        print(f"\n✅ Seeding complete:")
        print(f"   {investors_created} investors created")
        print(f"   {links_created} deal-investor links created")

    except Exception as e:
        session.rollback()
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == '__main__':
    seed_investors()
