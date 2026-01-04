#!/usr/bin/env python3
"""
Export deal tracker to HTML for GitHub Pages
Generates a beautiful, searchable HTML page from the master_list database
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import get_session, MasterItem, RawItem

def generate_deals_html(output_file=None):
    """
    Generate HTML page with all deals from master_list

    Args:
        output_file: Path to output HTML file (default: github_site/deals/index.html)
    """
    if output_file is None:
        script_dir = Path(__file__).parent
        output_file = script_dir.parent.parent / 'github_site' / 'deals' / 'index.html'
    else:
        output_file = Path(output_file)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Get deals from database
    session = get_session()
    try:
        deals = session.query(MasterItem, RawItem).join(
            RawItem, MasterItem.item_id == RawItem.id
        ).order_by(RawItem.published_date.desc()).all()

        print(f"Found {len(deals)} deals in master list")

        # Generate HTML
        html = generate_html_page(deals)

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✓ Exported {len(deals)} deals to {output_file}")
        return True

    except Exception as e:
        print(f"✗ Error exporting deals: {e}")
        return False
    finally:
        session.close()

def generate_html_page(deals):
    """Generate complete HTML page with deals"""

    # Calculate statistics
    total_deals = len(deals)
    sectors = {}
    capital_types = {}

    for master, raw in deals:
        if master.sector:
            sectors[master.sector] = sectors.get(master.sector, 0) + 1
        if master.capital_type:
            capital_types[master.capital_type] = capital_types.get(master.capital_type, 0) + 1

    # Generate table rows
    rows_html = []
    for master, raw in deals:
        date_str = raw.published_date.strftime('%Y-%m-%d') if raw.published_date else 'N/A'

        row = f"""
        <tr>
            <td>{date_str}</td>
            <td><strong>{master.company or 'N/A'}</strong></td>
            <td>{master.investment_amount or 'N/A'}</td>
            <td><span class="badge badge-primary">{master.capital_type or 'N/A'}</span></td>
            <td>{master.sector or 'N/A'}</td>
            <td>{master.project_type or 'N/A'}</td>
            <td>{master.location or 'N/A'}</td>
            <td>{master.summary or raw.rss_summary or 'N/A'}</td>
            <td><a href="{raw.url}" target="_blank">View</a></td>
        </tr>
        """
        rows_html.append(row)

    # Create filter options
    sector_options = ''.join([f'<option value="{s}">{s}</option>' for s in sorted(sectors.keys())])
    capital_options = ''.join([f'<option value="{c}">{c}</option>' for c in sorted(capital_types.keys())])

    # Complete HTML document
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Defense Private Capital Deals - Defense Capital Dashboard</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <nav>
        <div class="container">
            <a href="../index.html" class="logo">Defense Capital Dashboard</a>
            <button class="mobile-menu-toggle">☰</button>
            <ul>
                <li><a href="../index.html">Home</a></li>
                <li><a href="index.html" class="active">Deal Tracker</a></li>
                <li><a href="../charts/defense-investment.html">Defense Investment</a></li>
                <li><a href="../charts/defense-industrial.html">Defense Industrial</a></li>
                <li><a href="../charts/us-industrial.html">US Industrial</a></li>
            </ul>
        </div>
    </nav>

    <div class="container">
        <div class="page-header">
            <h1>Defense Private Capital Deals</h1>
            <p>Tracking venture capital, private equity, and corporate investments in the defense sector</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{total_deals}</div>
                <div class="stat-label">Total Deals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(sectors)}</div>
                <div class="stat-label">Sectors</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(capital_types)}</div>
                <div class="stat-label">Capital Types</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="last-updated">-</div>
                <div class="stat-label">Last Updated</div>
            </div>
        </div>

        <div class="card">
            <div class="search-filter-bar">
                <div class="search-box">
                    <input type="text" id="dealSearch" placeholder="Search deals...">
                </div>
                <div class="filter-group">
                    <label for="sectorFilter">Sector:</label>
                    <select id="sectorFilter">
                        <option value="">All Sectors</option>
                        {sector_options}
                    </select>
                </div>
                <div class="filter-group">
                    <label for="capitalFilter">Capital Type:</label>
                    <select id="capitalFilter">
                        <option value="">All Types</option>
                        {capital_options}
                    </select>
                </div>
            </div>

            <div style="overflow-x: auto;">
                <table id="dealsTable">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Company</th>
                            <th>Amount</th>
                            <th>Type</th>
                            <th>Sector</th>
                            <th>Project</th>
                            <th>Location</th>
                            <th>Summary</th>
                            <th>Link</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows_html)}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <footer>
        <p>Defense Capital Dashboard</p>
        <p>Data sourced from Google Alerts and public filings</p>
        <p>Last generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </footer>

    <script src="../js/main.js"></script>
    <script>
        // Initialize table features
        document.addEventListener('DOMContentLoaded', function() {{
            // Make table sortable
            ChartUtils.makeSortable(document.getElementById('dealsTable'));

            // Setup search
            ChartUtils.setupTableSearch('dealSearch', 'dealsTable');

            // Setup filters
            const sectorFilter = document.getElementById('sectorFilter');
            const capitalFilter = document.getElementById('capitalFilter');
            const table = document.getElementById('dealsTable');

            function applyFilters() {{
                const sector = sectorFilter.value.toLowerCase();
                const capital = capitalFilter.value.toLowerCase();
                const rows = table.querySelectorAll('tbody tr');

                rows.forEach(row => {{
                    const rowSector = row.cells[4].textContent.toLowerCase();
                    const rowCapital = row.cells[3].textContent.toLowerCase();

                    const sectorMatch = !sector || rowSector.includes(sector);
                    const capitalMatch = !capital || rowCapital.includes(capital);

                    row.style.display = sectorMatch && capitalMatch ? '' : 'none';
                }});
            }}

            sectorFilter.addEventListener('change', applyFilters);
            capitalFilter.addEventListener('change', applyFilters);

            // Update timestamp
            document.getElementById('last-updated').textContent = new Date().toLocaleDateString();
        }});
    </script>
</body>
</html>"""

    return html

if __name__ == '__main__':
    success = generate_deals_html()
    if not success:
        sys.exit(1)
