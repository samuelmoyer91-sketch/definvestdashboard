#!/usr/bin/env python3
"""
Import articles from Excel file into the triage system.
Reads the Raw_GA sheet and adds articles to raw_items, then scrapes them.
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import RawItem, get_session


def import_excel_articles(excel_path: str, sheet_name: str = 'Raw_GA'):
    """Import articles from Excel file into raw_items table."""

    # Read Excel file
    print(f"Reading Excel file: {excel_path}")
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    print(f"Found {len(df)} articles in sheet '{sheet_name}'")

    session = get_session()

    imported = 0
    skipped = 0

    for idx, row in df.iterrows():
        title = row['Title']
        url = row['URL']
        date_str = row['Date Created']
        summary = row['Summary'] if pd.notna(row['Summary']) else ''

        # Parse date
        try:
            published_date = pd.to_datetime(date_str)
        except:
            published_date = datetime.now()

        # Check if URL already exists
        existing = session.query(RawItem).filter_by(url=url).first()
        if existing:
            print(f"  Skip (exists): {title[:60]}...")
            skipped += 1
            continue

        # Create new raw item
        raw_item = RawItem(
            title=title,
            url=url,
            published_date=published_date,
            rss_summary=summary,
            feed_source='Excel Import',
            date_found=datetime.now()
        )

        session.add(raw_item)
        imported += 1
        print(f"  ✓ Imported: {title[:60]}...")

    session.commit()
    session.close()

    print(f"\n✅ Import complete!")
    print(f"   Imported: {imported}")
    print(f"   Skipped (duplicates): {skipped}")
    print(f"\nNext steps:")
    print(f"1. Run article scraper: python3 src/scraper/article_scraper.py")
    print(f"2. Review in triage UI: python3 src/web/app.py")


if __name__ == "__main__":
    import os

    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    excel_file = "Sheet with many articles that could be added to triage system.xlsx"

    if not Path(excel_file).exists():
        print(f"Error: Excel file not found: {excel_file}")
        sys.exit(1)

    import_excel_articles(excel_file)
