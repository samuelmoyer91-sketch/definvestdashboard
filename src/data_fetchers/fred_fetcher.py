#!/usr/bin/env python3
"""
FRED Data Fetcher
Fetches economic data from Federal Reserve Economic Data (FRED) API
"""

import json
import os
from datetime import datetime
from pathlib import Path
from fredapi import Fred
import pandas as pd

# FRED API configuration
# User will need to set this environment variable or edit this file
FRED_API_KEY = os.getenv('FRED_API_KEY', 'YOUR_API_KEY_HERE')

# FRED series to fetch (based on user's Google Sheets)
FRED_SERIES = {
    'FDEFX': {
        'name': 'National Defense Consumption Expenditures',
        'description': 'Federal defense spending',
        'units': 'Billions of Dollars'
    },
    'DRTSCILM': {
        'name': 'Net Percentage of Domestic Banks Tightening Standards for C&I Loans',
        'description': 'Bank lending standards for commercial loans',
        'units': 'Percent'
    },
    'DGORDER': {
        'name': 'Manufacturers\' New Orders: Durable Goods',
        'description': 'Defense goods orders',
        'units': 'Millions of Dollars'
    },
    'INDPRO': {
        'name': 'Industrial Production Index',
        'description': 'Overall industrial production',
        'units': 'Index 2017=100'
    },
    'PNFI': {
        'name': 'Private Nonresidential Fixed Investment',
        'description': 'Business investment in structures and equipment',
        'units': 'Billions of Dollars'
    },
    'ADEFNO': {
        'name': 'Manufacturers\' New Orders: Defense Aircraft',
        'description': 'Defense aircraft orders',
        'units': 'Millions of Dollars'
    },
    'ADAPNO': {
        'name': 'Manufacturers\' New Orders: Defense Aircraft Parts',
        'description': 'Defense aircraft parts orders',
        'units': 'Millions of Dollars'
    },
    'GPDI': {
        'name': 'Gross Private Domestic Investment',
        'description': 'GDP investment component',
        'units': 'Billions of Dollars'
    },
    'PRMFGCONS': {
        'name': 'Manufacturing Construction Spending',
        'description': 'Construction spending in manufacturing sector',
        'units': 'Millions of Dollars'
    },
    'IPB52300S': {
        'name': 'Industrial Production: Manufacturing (SIC)',
        'description': 'Industrial production metric for manufacturing',
        'units': 'Index 2017=100'
    }
}

def fetch_fred_data(api_key=None, output_dir=None):
    """
    Fetch all FRED series and save to JSON files

    Args:
        api_key: FRED API key (if None, uses env variable or default)
        output_dir: Output directory for JSON files (if None, uses ../github_site/data)
    """
    if api_key is None:
        api_key = FRED_API_KEY

    if api_key == 'YOUR_API_KEY_HERE':
        print("ERROR: FRED API key not set!")
        print("\nPlease either:")
        print("1. Set environment variable: export FRED_API_KEY='your_key_here'")
        print("2. Edit this file and replace YOUR_API_KEY_HERE with your key")
        print("\nGet a free API key at: https://fred.stlouisfed.org/docs/api/api_key.html")
        return False

    # Set output directory
    if output_dir is None:
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent.parent / 'github_site' / 'data'
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize FRED API
    try:
        fred = Fred(api_key=api_key)
        print(f"Connected to FRED API successfully")
    except Exception as e:
        print(f"ERROR: Failed to connect to FRED API: {e}")
        return False

    # Fetch each series
    results = {}
    for series_id, metadata in FRED_SERIES.items():
        try:
            print(f"Fetching {series_id}: {metadata['name']}...")

            # Get the data
            data = fred.get_series(series_id)

            # Convert to list of dicts for JSON
            data_list = []
            for date, value in data.items():
                if pd.notna(value):  # Skip NaN values
                    data_list.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'value': float(value)
                    })

            # Prepare output
            output = {
                'series_id': series_id,
                'name': metadata['name'],
                'description': metadata['description'],
                'units': metadata['units'],
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'data_points': len(data_list),
                'data': data_list
            }

            # Save to JSON file
            output_file = output_dir / f'{series_id.lower()}.json'
            with open(output_file, 'w') as f:
                json.dump(output, f, indent=2)

            print(f"  ✓ Saved {len(data_list)} data points to {output_file.name}")
            results[series_id] = len(data_list)

        except Exception as e:
            print(f"  ✗ ERROR fetching {series_id}: {e}")
            results[series_id] = 0

    # Save summary
    summary = {
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'series_count': len(FRED_SERIES),
        'series': results
    }

    summary_file = output_dir / 'fred_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n✓ Fetched {len(results)} FRED series")
    print(f"✓ Saved summary to {summary_file.name}")

    return True

if __name__ == '__main__':
    import sys

    # Check for API key argument
    api_key = sys.argv[1] if len(sys.argv) > 1 else None

    success = fetch_fred_data(api_key=api_key)

    if success:
        print("\n✓ FRED data fetch complete!")
    else:
        print("\n✗ FRED data fetch failed")
        sys.exit(1)
