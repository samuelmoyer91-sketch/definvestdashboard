#!/usr/bin/env python3
"""
Unified Publish Script for Defense Capital Dashboard
One command to update all data and generate the complete GitHub Pages site
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import subprocess

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")

def run_step(description, command, required=True):
    """
    Run a command and report success/failure

    Args:
        description: What this step does
        command: Command to run (as list)
        required: Whether to exit on failure
    """
    print(f"➤ {description}...")

    try:
        if isinstance(command, str):
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"  ✓ Success")
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        print(f"    {line}")
            return True
        else:
            print(f"  ✗ Failed")
            if result.stderr:
                for line in result.stderr.strip().split('\n')[:5]:  # Show first 5 lines
                    if line.strip():
                        print(f"    {line}")
            if required:
                print(f"\n✗ Required step failed. Aborting.")
                sys.exit(1)
            return False

    except Exception as e:
        print(f"  ✗ Error: {e}")
        if required:
            print(f"\n✗ Required step failed. Aborting.")
            sys.exit(1)
        return False

def check_api_key():
    """Check if FRED API key is configured"""
    api_key = os.getenv('FRED_API_KEY')
    if not api_key or api_key == 'YOUR_API_KEY_HERE':
        print("\n⚠️  WARNING: FRED API key not found!")
        print("\nTo fetch economic data, you need a free FRED API key:")
        print("1. Visit: https://fred.stlouisfed.org/docs/api/api_key.html")
        print("2. Sign up and get your API key")
        print("3. Set it: export FRED_API_KEY='your_key_here'")
        print("\nYou can still proceed to generate the site with existing data.")

        response = input("\nContinue without fetching new data? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
        return False
    return True

def main():
    """Main publish workflow"""

    print_header("Defense Capital Dashboard - Publish Script")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Get project root
    project_root = Path(__file__).parent
    os.chdir(project_root)

    print(f"Project directory: {project_root}\n")

    # Check for FRED API key
    has_api_key = check_api_key()

    # Step 1: Fetch FRED data (optional if no API key)
    print_header("Step 1: Fetch Economic Data")
    if has_api_key:
        run_step(
            "Fetching FRED economic data",
            [sys.executable, "src/data_fetchers/fred_fetcher.py"],
            required=False
        )
    else:
        print("  ⊘ Skipped (no API key)")

    # Step 2: Fetch financial data
    print_header("Step 2: Fetch Market Data")
    run_step(
        "Fetching stock/ETF data",
        [sys.executable, "src/data_fetchers/finance_fetcher.py"],
        required=False
    )

    # Step 2b: Fetch private capital data (VC and M&A)
    print_header("Step 2b: Fetch Private Capital Data")
    run_step(
        "Fetching VC and M&A data from Excel",
        [sys.executable, "src/data_fetchers/private_capital_fetcher.py"],
        required=False
    )

    # Step 3: Generate chart pages
    print_header("Step 3: Generate Chart Pages")
    run_step(
        "Generating HTML pages for all charts",
        [sys.executable, "src/export/generate_chart_pages_v2.py"],
        required=True
    )

    # Step 4: Export deal tracker
    print_header("Step 4: Export Deal Tracker")
    run_step(
        "Exporting deals from database to HTML",
        [sys.executable, "src/export/export_to_html.py"],
        required=True
    )

    # Step 5: Verify site structure
    print_header("Step 5: Verify Site Structure")

    github_site = project_root / 'github_site'
    required_files = [
        'index.html',
        'css/style.css',
        'js/main.js',
        'deals/index.html',
        'charts/defense-spending.html'
    ]

    all_present = True
    for file in required_files:
        file_path = github_site / file
        if file_path.exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} - MISSING")
            all_present = False

    if not all_present:
        print("\n⚠️  Some files are missing!")

    # Step 6: Count data files
    data_dir = github_site / 'data'
    if data_dir.exists():
        json_files = list(data_dir.glob('*.json'))
        print(f"\n  Data files: {len(json_files)} JSON files")
    else:
        print(f"\n  ⚠️  No data directory found")

    # Print summary
    print_header("Publish Complete!")

    print("Site location:")
    print(f"  {github_site}\n")

    print("Next steps:")
    print("  1. Test locally:")
    print(f"     cd {github_site}")
    print("     python3 -m http.server 8080")
    print("     Open: http://localhost:8080\n")

    print("  2. Push to GitHub:")
    print("     - Create a new PRIVATE repo: defense-dashboard")
    print("     - Initialize git in github_site/:")
    print(f"       cd {github_site}")
    print("       git init")
    print("       git add .")
    print('       git commit -m "Initial commit"')
    print("       git branch -M main")
    print("       git remote add origin https://github.com/samuelmoyer91-sketch/defense-dashboard.git")
    print("       git push -u origin main\n")

    print("  3. Enable GitHub Pages:")
    print("     - Go to repo Settings > Pages")
    print("     - Source: Deploy from branch 'main'")
    print("     - Folder: / (root)")
    print("     - Save\n")

    print("  4. Your site will be live at:")
    print("     https://samuelmoyer91-sketch.github.io/defense-dashboard/\n")

    print("⚠️  Remember: Keep repo PRIVATE until you review it!\n")

    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
