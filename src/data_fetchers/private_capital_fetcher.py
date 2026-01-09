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
    Extract VC, M&A, and Public Defense Companies data from Excel file and save as JSON

    Args:
        excel_file: Path to Excel file (default: Capital paper - first chart - investment trends.xlsx)
        output_dir: Output directory for JSON files (default: github_site/data)
    """
    if excel_file is None:
        script_dir = Path(__file__).parent
        excel_file = script_dir.parent.parent / 'Capital paper - first chart - investment trends.xlsx'
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
        # Read the Excel file (Sheet3 has the data)
        print("Reading Excel file...")
        df = pd.read_excel(excel_file, sheet_name='Sheet3', header=None)

        # Extract Public Defense Companies data (rows 15-20, columns 2-3)
        print("Fetching Public Defense Companies data...")
        pdc_data = []
        for idx in range(16, 21):  # Rows 16-20 (0-indexed)
            year = int(df.iloc[idx, 2])
            value = int(df.iloc[idx, 3])
            pdc_data.append({
                'date': f'{year}-12-31',
                'value': float(value)
            })

        pdc_output = {
            'series_id': 'PUBLIC_DEFENSE_COMPANIES',
            'name': 'Public Defense Companies',
            'description': 'Number of publicly traded defense and aerospace companies',
            'units': 'Count',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_points': len(pdc_data),
            'data': pdc_data
        }

        pdc_file = output_dir / 'public_defense_companies.json'
        with open(pdc_file, 'w') as f:
            json.dump(pdc_output, f, indent=2)
        print(f"  ✓ Saved {len(pdc_data)} Public Defense Companies data points to {pdc_file.name}")

        # Extract Venture Capital data (rows 15-20, column 4)
        print("Fetching VC investment data...")
        vc_data = []
        for idx in range(16, 21):
            year = int(df.iloc[idx, 2])
            value = int(df.iloc[idx, 4])
            vc_data.append({
                'date': f'{year}-12-31',
                'value': float(value)
            })

        vc_output = {
            'series_id': 'VC_DEFENSE',
            'name': 'Venture Capital Investment in Defense',
            'description': 'Annual venture capital investment in U.S. defense and dual-use companies',
            'units': 'Billions of Dollars',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_points': len(vc_data),
            'data': vc_data
        }

        vc_file = output_dir / 'vc_defense.json'
        with open(vc_file, 'w') as f:
            json.dump(vc_output, f, indent=2)
        print(f"  ✓ Saved {len(vc_data)} VC data points to {vc_file.name}")

        # Extract M&A data (rows 15-20, column 5)
        print("Fetching M&A activity data...")
        ma_data = []
        for idx in range(16, 21):
            year = int(df.iloc[idx, 2])
            value = int(df.iloc[idx, 5])
            ma_data.append({
                'date': f'{year}-12-31',
                'value': float(value)
            })

        ma_output = {
            'series_id': 'MA_DEFENSE',
            'name': 'M&A Activity in Defense',
            'description': 'Annual merger and acquisition activity in the U.S. aerospace and defense sector',
            'units': 'Billions of Dollars',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_points': len(ma_data),
            'data': ma_data
        }

        ma_file = output_dir / 'ma_defense.json'
        with open(ma_file, 'w') as f:
            json.dump(ma_output, f, indent=2)
        print(f"  ✓ Saved {len(ma_data)} M&A data points to {ma_file.name}")

        print(f"\n✓ Fetched all private capital data successfully (Public Defense Companies, VC, M&A)")
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
