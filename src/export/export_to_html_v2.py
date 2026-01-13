#!/usr/bin/env python3
"""
Export deal tracker to intelligence briefing-style HTML.

Generates a professional, paginated feed with AI summaries for government analysts.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import get_session, MasterItem, RawItem, AIExtraction

def generate_deals_html(output_file=None, deals_per_page=10):
    """
    Generate intelligence briefing-style HTML page.

    Args:
        output_file: Path to output HTML file
        deals_per_page: Number of deals to show per page
    """
    if output_file is None:
        script_dir = Path(__file__).parent
        output_file = script_dir.parent.parent / 'github_site' / 'deals' / 'index.html'
    else:
        output_file = Path(output_file)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Get deals with AI summaries
    session = get_session()
    try:
        deals = session.query(MasterItem, RawItem, AIExtraction).join(
            RawItem, MasterItem.item_id == RawItem.id
        ).outerjoin(
            AIExtraction, AIExtraction.item_id == RawItem.id
        ).order_by(RawItem.published_date.desc()).all()

        print(f"Found {len(deals)} deals in master list")

        # Generate HTML
        html = generate_html_page(deals, deals_per_page)

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✓ Exported {len(deals)} deals to {output_file}")
        return True

    except Exception as e:
        print(f"✗ Error exporting deals: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


def generate_html_page(deals, deals_per_page=10):
    """Generate intelligence briefing-style HTML"""

    # Build deal cards
    deal_cards = []
    for master, raw, ai in deals:
        card = generate_deal_card(master, raw, ai)
        deal_cards.append(card)

    deal_cards_html = '\n'.join(deal_cards)

    # Count deals with AI summaries
    ai_summary_count = sum(1 for _, _, ai in deals if ai and ai.summary_complete)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Defense Investment Activity - Defense Capital Dashboard</title>
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
                <li><a href="../charts/defense-investment.html">Defense Investment Trends</a></li>
                <li><a href="../charts/defense-industrial.html">Defense Industrial Health</a></li>
                <li><a href="../charts/us-industrial.html">Overall US Industrial Health</a></li>
            </ul>
        </div>
    </nav>

    <div class="container">
        <div class="page-header">
            <h1>Defense Investment Activity</h1>
            <p>Curated intelligence on venture capital, M&A, and funding activity in the defense sector</p>
            <p class="last-updated">Last updated: {datetime.now().strftime('%B %d, %Y')}</p>
        </div>

        <!-- Search/Filter Bar -->
        <div class="briefing-controls">
            <input type="text" id="searchBox" placeholder="Search deals..." class="search-input">
            <select id="dealTypeFilter" class="filter-select">
                <option value="all">All Deal Types</option>
                <option value="vc">Venture Capital</option>
                <option value="m&a">M&A / Acquisition</option>
                <option value="ipo">IPO</option>
                <option value="other">Other</option>
            </select>
        </div>

        <!-- Deal Feed -->
        <div id="dealFeed" class="briefing-feed">
            {deal_cards_html}
        </div>

        <!-- Pagination -->
        <div id="pagination" class="pagination"></div>

        <!-- Empty State -->
        <div id="emptyState" class="empty-state" style="display: none;">
            <p>No deals match your search criteria.</p>
        </div>
    </div>

    <footer>
        <p>Defense Capital Dashboard</p>
        <p>Deal intelligence curated from open sources</p>
    </footer>

    <script src="../js/main.js"></script>
    <script>
        // Pagination and filtering
        const searchBox = document.getElementById('searchBox');
        const dealTypeFilter = document.getElementById('dealTypeFilter');
        const dealFeed = document.getElementById('dealFeed');
        const deals = Array.from(dealFeed.querySelectorAll('.deal-card'));
        const emptyState = document.getElementById('emptyState');
        const paginationDiv = document.getElementById('pagination');

        const DEALS_PER_PAGE = {deals_per_page};
        let currentPage = 1;
        let filteredDeals = deals;

        function filterDeals() {{
            const searchTerm = searchBox.value.toLowerCase();
            const dealType = dealTypeFilter.value.toLowerCase();

            filteredDeals = deals.filter(deal => {{
                const text = deal.textContent.toLowerCase();
                const type = deal.dataset.dealType ? deal.dataset.dealType.toLowerCase() : '';

                const matchesSearch = text.includes(searchTerm);
                const matchesType = dealType === 'all' || type.includes(dealType);

                return matchesSearch && matchesType;
            }});

            currentPage = 1;
            renderPage();
        }}

        function renderPage() {{
            // Hide all deals
            deals.forEach(deal => deal.style.display = 'none');

            // Show deals for current page
            const start = (currentPage - 1) * DEALS_PER_PAGE;
            const end = start + DEALS_PER_PAGE;
            const pageDeals = filteredDeals.slice(start, end);

            pageDeals.forEach(deal => deal.style.display = 'block');

            // Update empty state
            emptyState.style.display = filteredDeals.length === 0 ? 'block' : 'none';

            // Render pagination controls
            renderPagination();

            // Scroll to top
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        function renderPagination() {{
            const totalPages = Math.ceil(filteredDeals.length / DEALS_PER_PAGE);

            if (totalPages <= 1) {{
                paginationDiv.innerHTML = '';
                return;
            }}

            let html = '<div class="pagination-controls">';

            // Previous button
            if (currentPage > 1) {{
                html += `<button class="page-btn" onclick="changePage(${{currentPage - 1}})">&larr; Previous</button>`;
            }}

            // Page numbers
            html += '<span class="page-info">Page ' + currentPage + ' of ' + totalPages + '</span>';

            // Next button
            if (currentPage < totalPages) {{
                html += `<button class="page-btn" onclick="changePage(${{currentPage + 1}})">Next &rarr;</button>`;
            }}

            html += '</div>';
            paginationDiv.innerHTML = html;
        }}

        function changePage(page) {{
            currentPage = page;
            renderPage();
        }}

        searchBox.addEventListener('input', filterDeals);
        dealTypeFilter.addEventListener('change', filterDeals);

        // Mobile menu toggle
        document.querySelector('.mobile-menu-toggle').addEventListener('click', function() {{
            document.querySelector('nav ul').classList.toggle('active');
        }});

        // Initial render
        renderPage();
    </script>
</body>
</html>"""

    return html


def generate_deal_card(master, raw, ai):
    """Generate HTML for a single deal card with improved UX"""

    # Extract date
    date_str = raw.published_date.strftime('%b %d, %Y') if raw.published_date else 'Date unknown'

    # Transaction Type badge (with fallback to old deal_type)
    deal_type = 'UNKNOWN'
    deal_type_class = 'badge-secondary'

    # Prioritize new transaction_type field
    if master and master.transaction_type:
        dt = master.transaction_type.upper()
        if 'FUNDING' in dt or 'EQUITY' in dt:
            deal_type = 'FUNDING'
            deal_type_class = 'badge-primary'
        elif 'ACQUISITION' in dt:
            deal_type = 'ACQUISITION'
            deal_type_class = 'badge-success'
        elif 'MERGER' in dt:
            deal_type = 'MERGER'
            deal_type_class = 'badge-success'
        elif 'IPO' in dt:
            deal_type = 'IPO'
            deal_type_class = 'badge-warning'
        elif 'CONTRACT' in dt or 'AWARD' in dt:
            deal_type = 'CONTRACT'
            deal_type_class = 'badge-info'
        elif 'PARTNERSHIP' in dt or 'JOINT' in dt:
            deal_type = 'PARTNERSHIP'
            deal_type_class = 'badge-info'
        elif 'INTERNAL' in dt:
            deal_type = 'INTERNAL'
            deal_type_class = 'badge-secondary'
        else:
            deal_type = dt[:20]
    # Fallback to old deal_type or AI extraction
    elif master and master.deal_type:
        dt = master.deal_type.upper()
        if 'VC' in dt or 'VENTURE' in dt or 'FUNDING' in dt:
            deal_type = 'FUNDING'
            deal_type_class = 'badge-primary'
        elif 'M&A' in dt or 'ACQUISITION' in dt or 'ACQUIRED' in dt:
            deal_type = 'ACQUISITION'
            deal_type_class = 'badge-success'
        elif 'IPO' in dt:
            deal_type = 'IPO'
            deal_type_class = 'badge-warning'
        else:
            deal_type = dt[:20]
    elif ai and ai.deal_type:
        dt = ai.deal_type.upper()
        if 'VC' in dt or 'VENTURE' in dt or 'FUNDING' in dt:
            deal_type = 'FUNDING'
            deal_type_class = 'badge-primary'
        elif 'M&A' in dt or 'ACQUISITION' in dt or 'ACQUIRED' in dt:
            deal_type = 'ACQUISITION'
            deal_type_class = 'badge-success'
        elif 'IPO' in dt:
            deal_type = 'IPO'
            deal_type_class = 'badge-warning'
        else:
            deal_type = dt[:20]

    # Extract company name from AI or master
    company_name = (ai.company if ai and ai.company else
                   master.company if master and master.company else None)

    # Build card with cleaner hierarchy
    card_html = f"""
    <div class="deal-card" data-deal-type="{deal_type.lower()}">
        <div class="deal-card-header">
            <div class="deal-meta-row">
                <span class="badge {deal_type_class}">{deal_type}</span>
                <span class="deal-date">{date_str}</span>
            </div>
        </div>

        <div class="deal-card-body">"""

    # Company headline (use curated company name from master, fallback to AI)
    company_display = master.company if master and master.company else company_name
    if company_display:
        card_html += f"""
            <h3 class="deal-company-name">{company_display}</h3>"""

    # Category badges (Capital Sources & Sectors)
    category_badges = []

    # Capital Sources (with fallback to old capital_type)
    if master and master.capital_sources:
        for source in master.capital_sources.split(','):
            category_badges.append(f'<span class="badge badge-info">{source.strip()}</span>')
    elif master and master.capital_type:
        category_badges.append(f'<span class="badge badge-info">{master.capital_type}</span>')

    # Sectors (with fallback to old sector)
    if master and master.sectors:
        for sector in master.sectors.split(','):
            category_badges.append(f'<span class="badge badge-success">{sector.strip()}</span>')
    elif master and master.sector:
        category_badges.append(f'<span class="badge badge-success">{master.sector}</span>')

    if category_badges:
        card_html += f"""
            <div class="deal-categories" style="margin-bottom: 12px;">
                {' '.join(category_badges)}
            </div>"""

    # Deal details (amount and investors) - use CURATED data from master, fallback to AI
    deal_details = []

    # Amount: prioritize master.investment_amount
    amount = master.investment_amount if master and master.investment_amount else (ai.deal_amount if ai else None)
    if amount:
        deal_details.append(f'<span class="deal-amount">{amount}</span>')

    # Investors: prioritize master.investors
    investors = master.investors if master and master.investors else (ai.investors if ai else None)
    if investors:
        deal_details.append(f'<span class="deal-investors">{investors}</span>')

    if deal_details:
        card_html += f"""
            <div class="deal-meta-info">
                {' • '.join(deal_details)}
            </div>"""

    # Use ONLY human-curated summary from master list
    # AI data and RSS summaries are NOT shown - only what you approved in triage
    if master and master.summary:
        # Simply display the curated summary as-is (no section parsing)
        card_html += f"""
            <div class="deal-insight">
                <p>{master.summary}</p>
            </div>"""
    else:
        # If no curated summary, show a placeholder
        card_html += f"""
            <div class="deal-insight">
                <p style="color: #999; font-style: italic;">No summary provided.</p>
            </div>"""

    # Footer with source link
    card_html += f"""
        </div>

        <div class="deal-card-footer">
            <a href="{raw.url}" target="_blank" rel="noopener" class="deal-source-link">
                Read Full Article →
            </a>
        </div>
    </div>"""

    return card_html


if __name__ == '__main__':
    import os
    os.chdir(Path(__file__).parent.parent.parent)

    generate_deals_html()
