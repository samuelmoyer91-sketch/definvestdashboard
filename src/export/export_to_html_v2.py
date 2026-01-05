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

        <!-- Summary Stats -->
        <div class="briefing-stats">
            <div class="stat-item">
                <div class="stat-number">{len(deals)}</div>
                <div class="stat-label">Total Deals</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{ai_summary_count}</div>
                <div class="stat-label">AI Analyzed</div>
            </div>
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

        <!-- Pagination (client-side JavaScript) -->
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
        // Simple client-side search and filter
        const searchBox = document.getElementById('searchBox');
        const dealTypeFilter = document.getElementById('dealTypeFilter');
        const dealFeed = document.getElementById('dealFeed');
        const deals = dealFeed.querySelectorAll('.deal-card');
        const emptyState = document.getElementById('emptyState');

        function filterDeals() {{
            const searchTerm = searchBox.value.toLowerCase();
            const dealType = dealTypeFilter.value.toLowerCase();
            let visibleCount = 0;

            deals.forEach(deal => {{
                const text = deal.textContent.toLowerCase();
                const type = deal.dataset.dealType ? deal.dataset.dealType.toLowerCase() : '';

                const matchesSearch = text.includes(searchTerm);
                const matchesType = dealType === 'all' || type.includes(dealType);

                if (matchesSearch && matchesType) {{
                    deal.style.display = '';
                    visibleCount++;
                }} else {{
                    deal.style.display = 'none';
                }}
            }});

            emptyState.style.display = visibleCount === 0 ? 'block' : 'none';
        }}

        searchBox.addEventListener('input', filterDeals);
        dealTypeFilter.addEventListener('change', filterDeals);

        // Mobile menu toggle
        document.querySelector('.mobile-menu-toggle').addEventListener('click', function() {{
            document.querySelector('nav ul').classList.toggle('active');
        }});
    </script>
</body>
</html>"""

    return html


def generate_deal_card(master, raw, ai):
    """Generate HTML for a single deal card"""

    # Extract date
    date_str = raw.published_date.strftime('%B %d, %Y') if raw.published_date else 'Date unknown'

    # Deal type badge
    deal_type = 'UNKNOWN'
    deal_type_class = 'badge-secondary'

    if ai and ai.deal_type:
        dt = ai.deal_type.upper()
        if 'VC' in dt or 'VENTURE' in dt:
            deal_type = 'VENTURE CAPITAL'
            deal_type_class = 'badge-primary'
        elif 'M&A' in dt or 'ACQUISITION' in dt or 'ACQUIRED' in dt:
            deal_type = 'M&A'
            deal_type_class = 'badge-success'
        elif 'IPO' in dt:
            deal_type = 'IPO'
            deal_type_class = 'badge-warning'
        else:
            deal_type = dt[:20]  # Truncate if too long

    # Build card content
    card_html = f"""
    <div class="deal-card" data-deal-type="{deal_type.lower()}">
        <div class="deal-header">
            <div class="deal-meta">
                <span class="badge {deal_type_class}">{deal_type}</span>
                <span class="deal-date">{date_str}</span>
            </div>
            <h2 class="deal-title">{raw.title}</h2>
        </div>

        <div class="deal-body">"""

    # Add AI summary if available
    if ai and ai.summary_complete:
        if ai.company and ai.company_description:
            card_html += f"""
            <div class="deal-company">
                <strong>{ai.company}</strong> &mdash; {ai.company_description}
            </div>"""

        deal_details = []
        if ai.deal_amount:
            deal_details.append(f"<strong>Amount:</strong> {ai.deal_amount}")
        if ai.investors:
            deal_details.append(f"<strong>Investors:</strong> {ai.investors}")

        if deal_details:
            card_html += f"""
            <div class="deal-details">
                {' &nbsp;|&nbsp; '.join(deal_details)}
            </div>"""

        if ai.strategic_significance:
            card_html += f"""
            <div class="deal-analysis">
                <strong>Strategic Significance:</strong> {ai.strategic_significance}
            </div>"""

        if ai.market_implications:
            card_html += f"""
            <div class="deal-implications">
                <strong>Market Implications:</strong> {ai.market_implications}
            </div>"""

    else:
        # Fallback to RSS summary if no AI summary
        if raw.rss_summary:
            card_html += f"""
            <div class="deal-summary">
                {raw.rss_summary}
            </div>"""

    # Always include source link
    card_html += f"""
        </div>

        <div class="deal-footer">
            <a href="{raw.url}" target="_blank" rel="noopener" class="source-link">
                Read Full Article &rarr;
            </a>
        </div>
    </div>"""

    return card_html


if __name__ == '__main__':
    import os
    os.chdir(Path(__file__).parent.parent.parent)

    generate_deals_html()
