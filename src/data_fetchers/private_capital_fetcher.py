#!/usr/bin/env python3
"""
Private Capital Data Fetcher
Extracts VC and M&A data from Excel file
"""

import json
from pathlib import Path
from datetime import datetime
import pandas as pd

def fetch_private_capital_data(excel_file=None, output_dir=None):
    """
    Extract VC and M&A data from Excel file and save as JSON

    Args:
        excel_file: Path to Excel file (default: Defense Private Capital Dashboard.xlsx)
        output_dir: Output directory for JSON files (default: github_site/data)
    """
    if excel_file is None:
        script_dir = Path(__file__).parent
        excel_file = script_dir.parent.parent / 'Defense Private Capital Dashboard.xlsx'
    else:
        excel_file = Path(excel_file)

    if output_dir is None:
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent.parent / 'github_site' / 'data'
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    if not excel_file.exists():
        print(f"ERROR: Excel file not found: {excel_file}")
        return False

    try:
        # Read VC data
        print("Fetching VC investment data...")
        vc_df = pd.read_excel(excel_file, sheet_name='VC')

        # Extract years and values (columns are: Year, 2023, 2022, 2021, 2020, 2019, ...)
        years = [col for col in vc_df.columns if isinstance(col, int)]
        values = vc_df.loc[0, years].values

        # Create data list (sorted by year ascending)
        vc_data = []
        for year, value in zip(years, values):
            if pd.notna(value):
                vc_data.append({
                    'date': f'{year}-12-31',  # End of year
                    'value': float(value)
                })

        # Sort by year
        vc_data.sort(key=lambda x: x['date'])

        vc_output = {
            'series_id': 'VC_DEFENSE',
            'name': 'Venture Capital Investment in Defense',
            'description': 'Annual venture capital investment in U.S. defense and dual-use companies',
            'units': 'Billions of Dollars',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_points': len(vc_data),
            'data': vc_data
        }

        # Save VC data
        vc_file = output_dir / 'vc_defense.json'
        with open(vc_file, 'w') as f:
            json.dump(vc_output, f, indent=2)
        print(f"  ✓ Saved {len(vc_data)} VC data points to {vc_file.name}")

        # Read M&A data
        print("Fetching M&A activity data...")
        ma_df = pd.read_excel(excel_file, sheet_name='M&A')

        # Extract years and values
        years = [col for col in ma_df.columns if isinstance(col, int)]
        values = ma_df.loc[0, years].values

        # Create data list
        ma_data = []
        for year, value in zip(years, values):
            if pd.notna(value):
                ma_data.append({
                    'date': f'{year}-12-31',
                    'value': float(value)
                })

        # Sort by year
        ma_data.sort(key=lambda x: x['date'])

        ma_output = {
            'series_id': 'MA_DEFENSE',
            'name': 'M&A Activity in Defense',
            'description': 'Annual merger and acquisition activity in the U.S. aerospace and defense sector',
            'units': 'Billions of Dollars',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_points': len(ma_data),
            'data': ma_data
        }

        # Save M&A data
        ma_file = output_dir / 'ma_defense.json'
        with open(ma_file, 'w') as f:
            json.dump(ma_output, f, indent=2)
        print(f"  ✓ Saved {len(ma_data)} M&A data points to {ma_file.name}")

        print(f"\n✓ Fetched private capital data successfully")
        return True

    except Exception as e:
        print(f"✗ Error fetching private capital data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import sys

    # Check for Excel file argument
    excel_file = sys.argv[1] if len(sys.argv) > 1 else None

    success = fetch_private_capital_data(excel_file=excel_file)

    if not success:
        sys.exit(1)
