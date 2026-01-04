"""Export master list to CSV for Google Sheets embedding."""

import csv
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import MasterItem, RawItem, get_session


def export_master_to_csv(output_path='exports/master_list.csv'):
    """Export master list to CSV file."""
    session = get_session()

    # Get all master items with their raw item data
    master_items = session.query(MasterItem).join(
        RawItem, MasterItem.item_id == RawItem.id
    ).order_by(
        RawItem.published_date.desc()  # Most recent first
    ).all()

    # Ensure export directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Write to CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'Date',
            'Company',
            'Investment Amount',
            'Capital Type',
            'Sector',
            'Location',
            'Project Type',
            'Summary',
            'Source URL'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for master in master_items:
            raw = session.query(RawItem).filter_by(id=master.item_id).first()

            writer.writerow({
                'Date': raw.published_date.strftime('%Y-%m-%d') if raw.published_date else 'N/A',
                'Company': master.company or 'N/A',
                'Investment Amount': master.investment_amount or 'Not disclosed',
                'Capital Type': master.capital_type or 'N/A',
                'Sector': master.sector or 'N/A',
                'Location': master.location or 'N/A',
                'Project Type': master.project_type or 'N/A',
                'Summary': master.summary if master.summary else 'N/A',
                'Source URL': raw.url
            })

    session.close()

    print("=" * 80)
    print(f"CSV EXPORT COMPLETE")
    print("=" * 80)
    print()
    print(f"Exported {len(master_items)} items to: {output_path}")
    print()
    print("Next steps:")
    print("1. Open Google Sheets")
    print("2. File → Import → Upload → Select this CSV file")
    print("3. On your Google Site, add a new page")
    print("4. Insert → Embed → paste the Google Sheets URL")
    print()

    return len(master_items)


def print_summary():
    """Print summary of master list for preview."""
    session = get_session()

    master_items = session.query(MasterItem).join(
        RawItem, MasterItem.item_id == RawItem.id
    ).order_by(
        RawItem.published_date.desc()
    ).all()

    print("=" * 80)
    print(f"MASTER LIST SUMMARY ({len(master_items)} items)")
    print("=" * 80)
    print()

    if not master_items:
        print("No items in master list yet.")
        print("Add items via the web interface at http://127.0.0.1:8000")
        session.close()
        return

    for i, master in enumerate(master_items[:5], 1):
        raw = session.query(RawItem).filter_by(id=master.item_id).first()
        print(f"{i}. {master.company or 'Unknown Company'}")
        print(f"   Investment: {master.investment_amount or 'Not disclosed'}")
        print(f"   Type: {master.capital_type or 'N/A'} | Sector: {master.sector or 'N/A'}")
        print(f"   Date: {raw.published_date.strftime('%Y-%m-%d') if raw.published_date else 'N/A'}")
        print()

    if len(master_items) > 5:
        print(f"... and {len(master_items) - 5} more items")
        print()

    session.close()


if __name__ == '__main__':
    import os
    os.chdir(Path(__file__).parent.parent.parent)

    if len(sys.argv) > 1 and sys.argv[1] == 'preview':
        print_summary()
    else:
        # Default output path
        output = sys.argv[1] if len(sys.argv) > 1 else 'exports/master_list.csv'
        export_master_to_csv(output)
