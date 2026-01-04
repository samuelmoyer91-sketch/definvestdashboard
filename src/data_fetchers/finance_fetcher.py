#!/usr/bin/env python3
"""
Financial Data Fetcher
Fetches stock/ETF data using yfinance and Treasury data from FRED
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import yfinance as yf
from fredapi import Fred
import pandas as pd

# Financial instruments to track
FINANCIAL_INSTRUMENTS = {
    'ITA': {
        'name': 'iShares U.S. Aerospace & Defense ETF',
        'description': 'Aerospace and Defense sector ETF',
        'type': 'ETF'
    },
    'XLI': {
        'name': 'Industrial Select Sector SPDR Fund',
        'description': 'Industrial sector ETF',
        'type': 'ETF'
    },
    'PLD': {
        'name': 'Prologis Inc.',
        'description': 'Industrial real estate company',
        'type': 'Stock'
    }
}

# Treasury yield from FRED
TREASURY_SERIES = {
    'DGS10': {
        'name': '10-Year Treasury Constant Maturity Rate',
        'description': '10-Year Treasury Yield',
        'units': 'Percent'
    }
}

def fetch_stock_data(ticker, period='5y', output_dir=None):
    """
    Fetch historical stock/ETF data

    Args:
        ticker: Stock ticker symbol
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        output_dir: Output directory for JSON files
    """
    try:
        print(f"Fetching {ticker}...")

        # Download data
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)

        # Convert to list of dicts
        data_list = []
        for date, row in hist.iterrows():
            data_list.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume'])
            })

        # Get metadata
        info = stock.info
        metadata = FINANCIAL_INSTRUMENTS.get(ticker, {})

        output = {
            'ticker': ticker,
            'name': metadata.get('name', info.get('longName', ticker)),
            'description': metadata.get('description', info.get('description', '')),
            'type': metadata.get('type', 'Stock'),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_points': len(data_list),
            'latest_close': data_list[-1]['close'] if data_list else None,
            'data': data_list
        }

        return output

    except Exception as e:
        print(f"  ✗ ERROR fetching {ticker}: {e}")
        return None

def fetch_treasury_data(api_key, series_id='DGS10', output_dir=None):
    """
    Fetch Treasury yield data from FRED

    Args:
        api_key: FRED API key
        series_id: FRED series ID for Treasury data
        output_dir: Output directory
    """
    try:
        print(f"Fetching {series_id} (Treasury Yield)...")

        fred = Fred(api_key=api_key)
        data = fred.get_series(series_id)

        # Convert to list of dicts
        data_list = []
        for date, value in data.items():
            if pd.notna(value):
                data_list.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'value': float(value)
                })

        metadata = TREASURY_SERIES[series_id]
        output = {
            'series_id': series_id,
            'name': metadata['name'],
            'description': metadata['description'],
            'units': metadata['units'],
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_points': len(data_list),
            'latest_value': data_list[-1]['value'] if data_list else None,
            'data': data_list
        }

        return output

    except Exception as e:
        print(f"  ✗ ERROR fetching {series_id}: {e}")
        return None

def fetch_all_financial_data(api_key=None, output_dir=None):
    """
    Fetch all financial data (stocks/ETFs and Treasury yields)

    Args:
        api_key: FRED API key (for Treasury data)
        output_dir: Output directory for JSON files
    """
    if output_dir is None:
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent.parent / 'github_site' / 'data'
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    # Fetch stock/ETF data
    for ticker in FINANCIAL_INSTRUMENTS.keys():
        data = fetch_stock_data(ticker, output_dir=output_dir)
        if data:
            output_file = output_dir / f'{ticker.lower()}.json'
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"  ✓ Saved {data['data_points']} data points to {output_file.name}")
            results[ticker] = data['data_points']
        else:
            results[ticker] = 0

    # Fetch Treasury data if API key provided
    if api_key and api_key != 'YOUR_API_KEY_HERE':
        for series_id in TREASURY_SERIES.keys():
            data = fetch_treasury_data(api_key, series_id, output_dir=output_dir)
            if data:
                output_file = output_dir / f'{series_id.lower()}.json'
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"  ✓ Saved {data['data_points']} data points to {output_file.name}")
                results[series_id] = data['data_points']
            else:
                results[series_id] = 0
    else:
        print("\nNote: Skipping Treasury data (FRED API key not provided)")
        print("Treasury data can be fetched separately with fred_fetcher.py")

    # Save summary
    summary = {
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'instruments_count': len(FINANCIAL_INSTRUMENTS),
        'instruments': results
    }

    summary_file = output_dir / 'finance_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n✓ Fetched {len(results)} financial instruments")
    print(f"✓ Saved summary to {summary_file.name}")

    return True

if __name__ == '__main__':
    import sys

    # Check for API key argument (optional for stocks, needed for Treasury)
    api_key = os.getenv('FRED_API_KEY', sys.argv[1] if len(sys.argv) > 1 else None)

    success = fetch_all_financial_data(api_key=api_key)

    if success:
        print("\n✓ Financial data fetch complete!")
    else:
        print("\n✗ Financial data fetch failed")
        sys.exit(1)
