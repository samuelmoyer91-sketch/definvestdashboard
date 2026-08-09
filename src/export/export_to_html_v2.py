#!/usr/bin/env python3
"""
Export deal tracker to intelligence briefing-style HTML.

Generates a professional, paginated feed with AI summaries for government analysts.

VISUAL DESIGN DOCUMENTATION:
===========================

Deal Card Structure:
-------------------
Each card follows a strict visual hierarchy designed for quick scanning:

1. HEADER (gray background):
   - Transaction type label (0.75rem, uppercase, teal, bold)
   - Date (0.85rem, gray, right-aligned)

2. BODY:
   - Company name (1.4rem, bold, near-black) - Most prominent element
   - Metadata section (labeled fields):
     * Labels: 0.75rem, uppercase, light gray (#94a3b8), block display
     * Values: 0.95rem, medium weight, dark (#1e293b), block display
     * Fields only show if data exists (graceful degradation)
     * Fields: Amount, Investors, Capital, Sectors
   - Summary (0.95rem, regular weight, good line height)

3. FOOTER (gray background):
   - Source link with domain attribution

Design Principles:
-----------------
- Labels and values are separate block elements (stack vertically)
- Small light labels, larger dark values for clear hierarchy
- Consistent spacing (0.75rem between fields)
- No badges or colors except for transaction type
- Clean text-based design that works with missing data
- Professional intelligence briefing aesthetic

Data Priority:
-------------
- Curated data from master_list takes priority
- AI-extracted data used as fallback for old deals
- RSS summaries never shown
- Only human-reviewed content appears on published dashboard
"""

import html as html_module
import json
import re
import sys
import os
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import get_session, MasterItem, RawItem, AIExtraction
from utils.dedup import parse_amount, detect_currency, fmt_amount


_UNKNOWN_VALUES = {'unknown', 'n/a', 'none', 'null', '-', ''}


def hero_amount(amount):
    """Compact USD figure for the card's headline slot: $2.5B, $144M, $28.5M.

    Parses (and FX-converts) via the shared parser, then trims trailing
    zeros from fmt_amount's output. Falls back to display_amount for
    unparseable values.
    """
    usd = parse_amount(amount)
    if not usd:
        return display_amount(amount)
    s = fmt_amount(usd)          # e.g. $2.50B / $144.0M
    s = re.sub(r'\.(\d*?)0+(?=[BMK]?$)', lambda m: '.' + m.group(1) if m.group(1) else '', s)
    return s


def display_amount(amount):
    """Render a deal amount for the public site as USD.

    Non-USD amounts are converted to USD (fixed rates) and shown as a clean
    dollar figure, e.g. "€110M" -> "$119M". USD amounts pass through as-is.
    Unparseable / "Not disclosed" text is returned unchanged.
    """
    if not is_known(amount):
        return amount
    code = detect_currency(amount)
    if code == 'USD':
        return amount
    usd = parse_amount(amount)  # already converted to USD by parse_amount
    if not usd:
        return amount  # unparseable currency amount — show original untouched
    return fmt_amount(usd)

# --- Region taxonomy for the deals-page region filter ----------------------
# Deliberately coarse: the job is "let me see European deals", not exhaustive
# geography. The US gets its own top-level region rather than sitting inside
# North America, because it is ~85% of the dataset and burying it would make
# the filter useless. Note this is a *taxonomy*, unlike the map's Europe view,
# which is a viewport box and so also frames Israel and Turkey.
_EUROPE = ('uk united kingdom england scotland wales northern ireland germany france italy spain '
           'portugal netherlands belgium luxembourg ireland sweden norway finland denmark iceland '
           'poland czechia slovakia hungary austria switzerland romania bulgaria greece croatia '
           'slovenia serbia estonia latvia lithuania ukraine cyprus malta').split()
_MIDEAST = 'israel turkey türkiye saudi arabia qatar jordan egypt lebanon'.split()
_APAC = ('india china japan taiwan singapore australia vietnam malaysia philippines indonesia '
         'thailand pakistan').split()

_MULTIWORD = {
    'united kingdom': 'Europe', 'northern ireland': 'Europe', 'czech republic': 'Europe',
    'north macedonia': 'Europe', 'bosnia and herzegovina': 'Europe',
    'saudi arabia': 'Middle East', 'united arab emirates': 'Middle East',
    'south korea': 'Asia-Pacific', 'new zealand': 'Asia-Pacific', 'sri lanka': 'Asia-Pacific',
    'south africa': 'Other', 'costa rica': 'Other',
}
_CANON = {'uk': 'United Kingdom', 'usa': 'United States', 'us': 'United States',
          'u.s.': 'United States', 'u.s.a.': 'United States', 'united states': 'United States',
          'england': 'United Kingdom', 'scotland': 'United Kingdom', 'wales': 'United Kingdom',
          'northern ireland': 'United Kingdom', 'türkiye': 'Turkey', 'czechia': 'Czech Republic'}
_US_STATE_NAMES = set(('alabama alaska arizona arkansas california colorado connecticut delaware florida '
    'georgia hawaii idaho illinois indiana iowa kansas kentucky louisiana maine maryland massachusetts '
    'michigan minnesota mississippi missouri montana nebraska nevada ohio oklahoma oregon pennsylvania '
    'tennessee texas utah vermont virginia washington wisconsin wyoming').split()) | {
    'new hampshire', 'new jersey', 'new mexico', 'new york', 'north carolina', 'north dakota',
    'rhode island', 'south carolina', 'south dakota', 'west virginia', 'district of columbia'}

# Explicit list, not "any two uppercase letters" — that heuristic reads the "UK"
# in "London, UK" as a US state abbreviation and files Britain under the US.
_US_STATE_ABBR = set(('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT '
                      'NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC').split())

REGION_ORDER = ['United States', 'Europe', 'Middle East', 'Asia-Pacific', 'Other']


def location_region(location):
    """Map a deal location string to (region, country) for filtering.

    Returns (None, None) for placeholders and multi-site strings, which should
    not be filed under any region. "Georgia" resolves to the US state here
    rather than the country, the opposite of the geocoder's choice — in this
    dataset a bare US state name is the overwhelmingly likely reading, and the
    geocoder only had to disambiguate because it was placing a map pin.
    """
    if not location:
        return None, None
    loc = location.strip()
    low = loc.lower()
    if low in _UNKNOWN_VALUES or low.startswith('multiple'):
        return None, None
    parts = [p.strip() for p in loc.split(',') if p.strip()]
    if not parts:
        return None, None
    last = parts[-1]
    ll = last.lower()

    if ll in ('usa', 'u.s.a.', 'us', 'u.s.', 'united states'):
        return 'United States', 'United States'
    if last.upper() in _US_STATE_ABBR or ll in _US_STATE_NAMES:
        return 'United States', 'United States'
    # "Austin Tx" — state abbreviation trailing without a comma
    toks = last.split()
    if len(toks) > 1 and toks[-1].upper() in _US_STATE_ABBR:
        return 'United States', 'United States'
    if ll in _MULTIWORD:
        return _MULTIWORD[ll], _CANON.get(ll, last.title())
    if ll in _EUROPE:
        return 'Europe', _CANON.get(ll, last.title())
    if ll in _MIDEAST:
        return 'Middle East', _CANON.get(ll, last.title())
    if ll in _APAC:
        return 'Asia-Pacific', _CANON.get(ll, last.title())
    return 'Other', _CANON.get(ll, last.title())


def is_known(val):
    """Return True if val is a non-empty, non-placeholder string."""
    return bool(val) and str(val).strip().lower() not in _UNKNOWN_VALUES

def e(val):
    """HTML-escape a value for safe embedding in markup."""
    return html_module.escape(str(val)) if val else ''


def extract_domain(url):
    """Extract clean domain from URL for source attribution.

    Handles Google News redirect URLs by extracting the actual destination.

    Examples:
        'https://www.wsj.com/articles/...' -> 'wsj.com'
        'https://google.com/url?...&url=https://wsj.com/...' -> 'wsj.com'
    """
    try:
        # Handle Google News redirect URLs
        if 'google.com/url?' in url:
            # Extract the actual URL from the redirect
            from urllib.parse import parse_qs
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if 'url' in params:
                # Use the actual destination URL
                url = params['url'][0]

        # Extract domain from URL
        parsed = urlparse(url)
        domain = parsed.netloc

        # Remove 'www.' prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]

        # Collapse deep subdomain chains to the registrable root for display
        # (keeps short second-level TLDs like co.uk intact: a.b.co.uk -> b.co.uk)
        parts = domain.split('.')
        if len(parts) > 2:
            keep = 3 if (len(parts[-2]) <= 3 and len(parts[-1]) <= 3) else 2
            domain = '.'.join(parts[-keep:])

        return domain if domain else 'source'
    except:
        return 'source'


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
        deals = session.query(MasterItem, RawItem, AIExtraction).filter(
            MasterItem.removed_at.is_(None)   # skip soft-deleted duplicates
        ).join(
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

    # Fixed display order for the region filter (see REGION_ORDER)
    region_order_js = json.dumps(REGION_ORDER)

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
    <link rel="icon" type="image/svg+xml" href="../favicon.svg">
    <link rel="stylesheet" href="../css/style.css">
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-CS5MJEVNGN"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-CS5MJEVNGN');
    </script>
</head>
<body>
    <nav>
        <div class="container">
            <a href="../index.html" class="logo" style="display: flex; align-items: center; gap: 10px;">
                <svg width="24" height="24" viewBox="0 0 64 64" fill="none" aria-hidden="true">
                    <rect x="4" y="4" width="16" height="16" rx="2" stroke="white" stroke-width="1.5" opacity="0.15"/>
                    <rect x="24" y="4" width="16" height="16" rx="2" stroke="white" stroke-width="1.5" opacity="0.15"/>
                    <rect x="44" y="4" width="16" height="16" rx="2" stroke="white" stroke-width="1.5" opacity="0.25"/>
                    <rect x="4" y="24" width="16" height="16" rx="2" stroke="white" stroke-width="1.5" opacity="0.15"/>
                    <rect x="24" y="24" width="16" height="16" rx="2" stroke="white" stroke-width="1.5" opacity="0.35"/>
                    <rect x="44" y="24" width="16" height="16" rx="2" fill="white" opacity="0.55"/>
                    <rect x="4" y="44" width="16" height="16" rx="2" stroke="white" stroke-width="1.5" opacity="0.25"/>
                    <rect x="24" y="44" width="16" height="16" rx="2" fill="white" opacity="0.55"/>
                    <rect x="44" y="44" width="16" height="16" rx="2" fill="white"/>
                </svg>
                Defense Capital Dashboard
            </a>
            <button class="mobile-menu-toggle" aria-label="Toggle navigation">☰</button>
            <ul>
                <li><a href="../index.html">Home</a></li>
                <li><a href="index.html" class="active">Deal Tracker</a></li>
                <li><a href="map.html">Deal Map</a></li>
                <li><a href="../charts/indicators.html">Indicators</a></li>
            </ul>
        </div>
    </nav>

    <div class="page-header">
        <div class="page-header-inner">
            <p class="page-header-title">Curated intelligence on venture capital, M&amp;A, and funding activity in the defense sector</p>
            <p class="page-header-updated">Last updated: {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
    </div>

    <div class="container">
        <!-- Search & Filter Controls -->
        <div class="briefing-controls">
            <input type="text" id="searchBox" placeholder="Search deals..." class="search-input">
            <select id="sectorFilter" class="filter-select">
                <option value="">All Sectors</option>
            </select>
            <select id="capitalFilter" class="filter-select">
                <option value="">All Capital Types</option>
            </select>
            <select id="regionFilter" class="filter-select">
                <option value="">All Regions</option>
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
        <p><strong>Defense Capital Dashboard</strong></p>
        <p>Deal intelligence curated from open sources</p>
        <p style="font-size: 0.75rem; opacity: 0.7; margin-top: 0.5rem;">This product uses the FRED&reg; API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.</p>
        <p>Created by Sam Moyer | <a href="https://github.com/samuelmoyer91-sketch" target="_blank" rel="noopener noreferrer">GitHub</a> | <a href="mailto:samuel.moyer91@gmail.com">samuel.moyer91@gmail.com</a></p>
    </footer>

    <script src="../js/main.js"></script>
    <script>
        // Pagination and filtering
        const searchBox = document.getElementById('searchBox');
        const sectorFilter = document.getElementById('sectorFilter');
        const capitalFilter = document.getElementById('capitalFilter');
        const regionFilter = document.getElementById('regionFilter');
        const dealFeed = document.getElementById('dealFeed');
        const deals = Array.from(dealFeed.querySelectorAll('.deal-card'));
        const emptyState = document.getElementById('emptyState');
        const paginationDiv = document.getElementById('pagination');

        const DEALS_PER_PAGE = {deals_per_page};
        let currentPage = 1;
        let filteredDeals = deals;

        // Merge aliases into canonical slugs
        const sectorAliases = {{
            'ai': 'ai-ml',
            'materials': 'advanced-materials',
            'mineral-refining': 'advanced-materials'
        }};
        const capitalAliases = {{
            'corporate-investment': 'internal-self-funded',
            'grant-sbir': 'government-contract',
            'government-support': 'government-contract'
        }};
        function normalizeSector(s) {{
            return sectorAliases[s] || s;
        }}
        function normalizeCapital(c) {{
            return capitalAliases[c] || c;
        }}

        // Populate filter dropdowns from card data attributes
        (function populateFilters() {{
            // Canonical labels for display (slug -> label; missing slugs fall back to the slug)
            const sectorLabels = {{
                'autonomous-systems-drones': 'Autonomous Systems/Drones',
                'ai-ml': 'AI/ML',
                'quantum': 'Quantum',
                'software-it': 'Software/IT',
                'cybersecurity': 'Cybersecurity',
                'communications': 'Communications',
                'sensors-isr': 'Sensors/ISR',
                'electronic-warfare': 'Electronic Warfare',
                'space-satellites': 'Space/Satellites',
                'aerospace': 'Aerospace',
                'propulsion-engines': 'Propulsion/Engines',
                'maritime-naval': 'Maritime/Naval',
                'ground-vehicles': 'Ground Vehicles',
                'munitions-weapons': 'Munitions/Weapons',
                'semiconductors-electronics': 'Semiconductors/Electronics',
                'advanced-materials': 'Advanced Materials',
                'critical-minerals': 'Critical Minerals',
                'energy-power': 'Energy/Power',
                'manufacturing-production': 'Manufacturing/Production',
                'logistics-sustainment': 'Logistics/Sustainment',
                'biotech-medical': 'Biotech/Medical',
                'other': 'Other'
            }};
            const capitalLabels = {{
                'seed': 'Seed',
                'venture-capital': 'Venture Capital',
                'private-equity': 'Private Equity',
                'corporate-venture': 'Corporate Venture',
                'corporate-m-a': 'Corporate M&A',
                'government-contract': 'Government Support',
                'public-markets': 'Public Markets',
                'internal-self-funded': 'Internal/Self-Funded',
                'fund-raise': 'Fund Raise',
                'family-office': 'Family Office',
                'strategic-partner': 'Strategic Partner'
            }};

            const sectorCounts = {{}};
            const capitalCounts = {{}};

            deals.forEach(deal => {{
                const sectors = deal.dataset.sectors;
                if (sectors) {{
                    sectors.split(',').forEach(s => {{
                        const ns = normalizeSector(s);
                        sectorCounts[ns] = (sectorCounts[ns] || 0) + 1;
                    }});
                }}
                const capital = deal.dataset.capital;
                if (capital) {{
                    capital.split(',').forEach(c => {{
                        const nc = normalizeCapital(c);
                        capitalCounts[nc] = (capitalCounts[nc] || 0) + 1;
                    }});
                }}
            }});

            Object.keys(sectorCounts).sort((a, b) => {{
                const la = sectorLabels[a] || a;
                const lb = sectorLabels[b] || b;
                return la.localeCompare(lb);
            }}).forEach(slug => {{
                const opt = document.createElement('option');
                opt.value = slug;
                opt.textContent = (sectorLabels[slug] || slug) + ' (' + sectorCounts[slug] + ')';
                sectorFilter.appendChild(opt);
            }});

            Object.keys(capitalCounts).sort((a, b) => {{
                const la = capitalLabels[a] || a;
                const lb = capitalLabels[b] || b;
                return la.localeCompare(lb);
            }}).forEach(slug => {{
                const opt = document.createElement('option');
                opt.value = slug;
                opt.textContent = (capitalLabels[slug] || slug) + ' (' + capitalCounts[slug] + ')';
                capitalFilter.appendChild(opt);
            }});

            // Region filter: each region is selectable in its own right, with the
            // countries present in the data nested beneath it. Values are prefixed
            // r: / c: so filterDeals knows which attribute to match against.
            const regionOrder = {region_order_js};
            const regionCounts = {{}};
            const countryCounts = {{}};
            deals.forEach(deal => {{
                const r = deal.dataset.region;
                const c = deal.dataset.country;
                if (!r) return;
                regionCounts[r] = (regionCounts[r] || 0) + 1;
                countryCounts[r] = countryCounts[r] || {{}};
                if (c) countryCounts[r][c] = (countryCounts[r][c] || 0) + 1;
            }});
            regionOrder.forEach(region => {{
                if (!regionCounts[region]) return;
                const group = document.createElement('optgroup');
                group.label = region;
                const all = document.createElement('option');
                all.value = 'r:' + region;
                all.textContent = 'All ' + region + ' (' + regionCounts[region] + ')';
                group.appendChild(all);
                const countries = Object.keys(countryCounts[region] || {{}});
                // A region whose only country label repeats the region name (the US)
                // needs no sub-list.
                if (!(countries.length === 1 && countries[0] === region)) {{
                    countries.sort((a, b) => a.localeCompare(b)).forEach(c => {{
                        const opt = document.createElement('option');
                        opt.value = 'c:' + c;
                        opt.textContent = '\\u00A0\\u00A0' + c + ' (' + countryCounts[region][c] + ')';
                        group.appendChild(opt);
                    }});
                }}
                regionFilter.appendChild(group);
            }});
        }})();

        function filterDeals() {{
            const searchTerm = searchBox.value.toLowerCase();
            const sectorVal = sectorFilter.value;
            const capitalVal = capitalFilter.value;
            const regionVal = regionFilter.value;

            filteredDeals = deals.filter(deal => {{
                const matchesSearch = deal.textContent.toLowerCase().includes(searchTerm);
                const matchesSector = !sectorVal || (deal.dataset.sectors && deal.dataset.sectors.split(',').map(normalizeSector).includes(sectorVal));
                const matchesCapital = !capitalVal || (deal.dataset.capital && deal.dataset.capital.split(',').map(normalizeCapital).includes(capitalVal));
                const matchesRegion = !regionVal || (regionVal.startsWith('r:')
                    ? deal.dataset.region === regionVal.slice(2)
                    : deal.dataset.country === regionVal.slice(2));
                return matchesSearch && matchesSector && matchesCapital && matchesRegion;
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
        sectorFilter.addEventListener('change', filterDeals);
        capitalFilter.addEventListener('change', filterDeals);
        regionFilter.addEventListener('change', filterDeals);

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

    # Extract company name from AI or master
    company_name = (ai.company if ai and ai.company else
                   master.company if master and master.company else None)

    # Extract sectors and capital sources early (used for both data attrs and display)
    capital_sources = None
    if master and master.capital_sources:
        capital_sources = master.capital_sources
    elif master and master.capital_type:
        capital_sources = master.capital_type

    sectors = None
    if master and master.sectors:
        sectors = master.sectors
    elif master and master.sector:
        sectors = master.sector

    # Location: from master_list (curated in triage), fallback to AI extraction.
    # Resolved here rather than at its display site because the region filter
    # needs it on the card's opening tag.
    location = master.location if master and master.location else (ai.location if ai else None)
    region, country = location_region(location)

    # Build data attributes for filtering
    def slugify(val):
        return re.sub(r'[\s/]+', '-', val.strip().lower())

    sectors_attr = ''
    if sectors:
        sector_slugs = ','.join(slugify(s) for s in re.split(r',\s*', sectors))
        sectors_attr = f' data-sectors="{sector_slugs}"'

    capital_attr = ''
    if capital_sources:
        capital_slugs = ','.join(slugify(s) for s in re.split(r',\s*', capital_sources))
        capital_attr = f' data-capital="{capital_slugs}"'

    region_attr = f' data-region="{e(region)}" data-country="{e(country)}"' if region else ''

    # Build card with clean text-based layout
    card_html = f"""
    <div class="deal-card"{sectors_attr}{capital_attr}{region_attr}>
        <div class="deal-card-header">
            <div class="deal-header-line">
                <span class="deal-date">{date_str}</span>
            </div>
        </div>

        <div class="deal-card-body">"""

    # Deal title priority: curated > AI-rewritten > raw RSS
    if master and master.title:
        title_display = master.title
    elif ai and ai.title:
        title_display = ai.title
    else:
        title_display = raw.title
        # Strip publication name suffixes from raw RSS titles (e.g., "- SpaceNews", "| Aviation Week")
        if title_display:
            title_display = re.split(r'\s+[-|–—]\s+(?=[A-Z][\w\s]*$)', title_display)[0].strip()
    # Strip any HTML tags leaked from RSS (e.g., <b> from Google News)
    if title_display:
        title_display = re.sub(r'</?[^>]+>', '', title_display)

    # Amount is the headline number for a capital tracker: render it as a
    # visual hero beside the title, not as one more metadata row.
    amount = master.investment_amount if master and master.investment_amount else (ai.deal_amount if ai else None)
    amount_hero = f"""
                <span class="deal-amount-hero">{e(hero_amount(amount))}</span>""" if is_known(amount) else ''

    heading = title_display or company_name
    if heading:
        card_html += f"""
            <div class="deal-title-row">
                <h3 class="deal-company-name">{e(heading)}</h3>{amount_hero}
            </div>"""
    elif amount_hero:
        card_html += f"""
            <div class="deal-title-row">{amount_hero}
            </div>"""

    # Start metadata section
    card_html += """
            <div class="deal-metadata">"""

    # Investors: prioritize master.investors
    investors = master.investors if master and master.investors else (ai.investors if ai else None)
    if is_known(investors):
        card_html += f"""
                <div class="deal-meta-line">
                    <span class="meta-label">Investors</span>
                    <span>{e(investors)}</span>
                </div>"""

    # Capital Sources (already extracted above for data attributes)
    if is_known(capital_sources):
        capital_display = capital_sources.replace(',', ', ')
        card_html += f"""
                <div class="deal-meta-line">
                    <span class="meta-label">Capital</span>
                    <span>{e(capital_display)}</span>
                </div>"""

    # Sectors (already extracted above for data attributes) — rendered as chips
    if is_known(sectors):
        chips = ''.join(
            f'<span class="sector-chip">{e(s.strip())}</span>'
            for s in re.split(r',\s*', sectors) if s.strip()
        )
        card_html += f"""
                <div class="deal-meta-line">
                    <span class="meta-label">Sectors</span>
                    <span class="sector-chips">{chips}</span>
                </div>"""

    # Location (resolved above, alongside the other data attributes)
    if is_known(location):
        card_html += f"""
                <div class="deal-meta-line">
                    <span class="meta-label">Location</span>
                    <span>{e(location)}</span>
                </div>"""

    # Close metadata section
    card_html += """
            </div>"""

    # Use ONLY human-curated summary from master list
    # AI data and RSS summaries are NOT shown - only what you approved in triage
    if master and is_known(master.summary):
        card_html += f"""
            <div class="deal-insight">
                <p>{e(master.summary)}</p>
            </div>"""

    # Footer with source link (includes domain attribution)
    primary_url = master.source_url if master and master.source_url else raw.canonical_url
    primary_domain = extract_domain(primary_url)
    card_html += f"""
        </div>

        <div class="deal-card-footer">
            <a href="{primary_url}" target="_blank" rel="noopener" class="deal-source-link">
                Read Full Article on {primary_domain} →
            </a>"""

    if master and master.additional_source_url:
        add_domain = extract_domain(master.additional_source_url)
        card_html += f"""
            <a href="{master.additional_source_url}" target="_blank" rel="noopener" class="deal-source-link" style="margin-left: 1rem;">
                Also: {add_domain} →
            </a>"""

    card_html += """
        </div>
    </div>"""

    return card_html


if __name__ == '__main__':
    import os
    os.chdir(Path(__file__).parent.parent.parent)

    generate_deals_html()
