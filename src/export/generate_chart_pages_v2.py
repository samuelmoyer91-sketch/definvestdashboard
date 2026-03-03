#!/usr/bin/env python3
"""
Generate HTML pages for all charts with reorganized navigation
Creates individual chart pages and category overview pages
"""

from pathlib import Path

# Navigation categories with key insights
CATEGORIES = {
    'defense-investment': {
        'title': 'Capital Flows',
        'description': 'Tracking capital flows and investment activity in the defense sector',
        'charts': ['dgorder', 'public_defense_companies', 'vc_defense', 'ma_defense'],
        'insights': [
            'Defense capital goods orders provide early signals of future production activity and contractor revenue',
            'VC investment trends indicate emerging technology areas attracting private capital in defense',
            'M&A activity reflects industry consolidation and strategic positioning for major defense programs'
        ]
    },
    'defense-industrial': {
        'title': 'Industrial Capacity',
        'description': 'Measuring the production capacity and health of the defense industrial base',
        'charts': ['adefno', 'adapno', 'ipb52300s', 'fdefx', 'prmfgcons', 'ita'],
        'insights': [
            'Aircraft orders and production volumes indicate the health of major defense aerospace programs',
            'Defense equipment production levels show current output capacity of the industrial base',
            'Federal defense spending drives contractor revenues and investment in production capacity',
            'Manufacturing construction reflects long-term capacity expansion in defense-critical facilities'
        ]
    },
    'us-industrial': {
        'title': 'Macro Environment',
        'description': 'Broader economic indicators affecting defense manufacturing capabilities',
        'charts': ['indpro', 'pnfi', 'gpdi', 'drtscilm', 'xli', 'pld', 'dgs10'],
        'insights': [
            'Overall industrial production indicates the health of the manufacturing base supporting defense',
            'Business investment trends signal confidence and capacity expansion across the industrial economy',
            'Bank lending standards affect access to capital for defense contractors and suppliers',
            'Treasury yields influence borrowing costs for major defense programs and contractor financing'
        ]
    }
}

# Default date range for consistent visualization (2019-present)
# Charts with limited data (VC, M&A, Public Defense Companies) will show all available data
DEFAULT_START_DATE = '2019-01-01'

# Y-axis formatting configuration
# Format: {'prefix': '$', 'suffix': 'B', 'divisor': 1000} means divide value by 1000 and show as $XB
Y_AXIS_FORMATS = {
    # Trillions (divide billions by 1000)
    'gpdi': {'prefix': '$', 'suffix': 'T', 'divisor': 1000},
    'pnfi': {'prefix': '$', 'suffix': 'T', 'divisor': 1000},
    # Billions (divide millions by 1000)
    'dgorder': {'prefix': '$', 'suffix': 'B', 'divisor': 1000},
    'adefno': {'prefix': '$', 'suffix': 'B', 'divisor': 1000},
    'adapno': {'prefix': '$', 'suffix': 'B', 'divisor': 1000},
    'prmfgcons': {'prefix': '$', 'suffix': 'B', 'divisor': 1000},
    # Billions (already in billions)
    'vc_defense': {'prefix': '$', 'suffix': 'B', 'divisor': 1},
    'public_defense_companies': {'prefix': '$', 'suffix': 'B', 'divisor': 1},
    'ma_defense': {'prefix': '$', 'suffix': 'B', 'divisor': 1},
    'fdefx': {'prefix': '$', 'suffix': 'B', 'divisor': 1},
    # USD prices
    'ita': {'prefix': '$', 'suffix': '', 'divisor': 1},
    'xli': {'prefix': '$', 'suffix': '', 'divisor': 1},
    'pld': {'prefix': '$', 'suffix': '', 'divisor': 1},
    # Percentages
    'drtscilm': {'prefix': '', 'suffix': '%', 'divisor': 1},
    'dgs10': {'prefix': '', 'suffix': '%', 'divisor': 1},
    # Indexes (no formatting)
    'ipb52300s': {'prefix': '', 'suffix': '', 'divisor': 1},
    'indpro': {'prefix': '', 'suffix': '', 'divisor': 1},
}

# Chart definitions with user's original descriptions
CHARTS = {
    'dgorder': {
        'title': 'Defense Capital Goods Orders',
        'subtitle': "Manufacturers' new orders for defense capital goods",
        'description': """
            Manufacturers' New Orders: Defense Capital Goods is a data set released monthly by the US Census Bureau.
            This data set tracks how much money US manufacturers are receiving in new orders for military equipment and technology,
            from aircraft and missiles to small arms and communication systems. It gives us a snapshot of how active the defense
            industry is at any given time.
        """,
        'context': """
            Because these are long-term, high-value items, an increase in orders usually reflects a boost in government spending
            or a shift in national defense priorities. When new orders rise, it can indicate that the government is preparing for
            future defense needs or responding to global tensions. On the flip side, a drop might suggest tightening budgets or
            changes in sentiment in industry.
        """,
        'units': 'Millions of Dollars',
        'category': 'defense-investment'
    },
    'vc_defense': {
        'title': 'Venture Capital Investment in Defense',
        'subtitle': 'Annual VC investment in defense and dual-use companies',
        'description': """
            Venture Capital Investment in Defense tracks the volume of venture capital dollars flowing into U.S.
            defense-focused and dual-use companies. This data is updated annually and reflects early-stage investment activity
            in defense technology and innovation.
        """,
        'context': """
            Venture capital funding is a leading indicator of innovation and emerging technologies in the defense sector. Rising VC
            investment suggests strong investor interest in defense tech startups, often in areas like AI, cybersecurity, autonomous
            systems, and space. This capital fuels the next generation of defense capabilities and can signal where the market sees
            future growth opportunities.
        """,
        'units': 'Billions of Dollars',
        'category': 'defense-investment'
    },
    'public_defense_companies': {
        'title': 'Public Defense Companies - Capex & R&D',
        'subtitle': 'Capital expenditures and R&D investment by publicly traded defense companies',
        'description': """
            Public Defense Companies - Capex & R&D tracks the annual capital expenditures and research & development
            investment by publicly traded defense and aerospace companies. This measures how much these companies are investing in
            facilities, equipment, and innovation to support future growth and capabilities.
        """,
        'context': """
            Rising capex and R&D spending by public defense companies signals confidence in future demand and strategic positioning for
            major programs. These investments build manufacturing capacity, develop next-generation technologies, and modernize production
            facilities. Strong investment levels indicate a healthy, growing defense industrial base preparing for long-term demand.
            Declining investment may suggest caution about future budgets or industry consolidation reducing the number of major programs.
        """,
        'units': 'Billions of Dollars',
        'category': 'defense-investment'
    },
    'ma_defense': {
        'title': 'M&A Activity in Defense',
        'subtitle': 'Annual merger and acquisition activity in aerospace and defense',
        'description': """
            M&A Activity in Defense tracks the dollar value of mergers and acquisitions in the U.S. aerospace and
            defense sector. This includes private equity buyouts, strategic acquisitions by defense primes, and consolidation activity
            across the defense industrial base.
        """,
        'context': """
            M&A activity reflects consolidation trends, capital deployment by private equity and strategic buyers, and the overall
            health of the defense sector. High M&A volumes can indicate strong valuations, buyer confidence, and strategic positioning
            for future defense programs. Tracking M&A helps identify which segments of the defense industrial base are seeing the most
            investment interest and consolidation.
        """,
        'units': 'Billions of Dollars',
        'category': 'defense-investment'
    },
    'adefno': {
        'title': 'Defense Aircraft Orders',
        'subtitle': "Manufacturers' new orders for defense aircraft",
        'description': """
            Defense Aircraft Orders (ADEFNO) tracks new orders for complete military aircraft from manufacturers.
            This includes fighter jets, transport aircraft, helicopters, and other defense aviation platforms. These are typically
            large, multi-year contracts that represent major defense procurement programs.
        """,
        'context': """
            Aircraft orders are often the largest single-item defense purchases and provide visibility into future aerospace sector
            performance. Major programs can span decades and involve thousands of workers. Rising aircraft orders signal strong
            demand for air superiority, transport capability, or modernization of aging fleets.
        """,
        'units': 'Millions of Dollars',
        'category': 'defense-industrial'
    },
    'adapno': {
        'title': 'Defense Aircraft Parts Orders',
        'subtitle': "Manufacturers' new orders for defense aircraft parts and components",
        'description': """
            Defense Aircraft Parts Orders (ADAPNO) measures orders for aircraft components, subassemblies, and
            replacement parts used in military aviation. This includes everything from engines and avionics to structural components
            and weapons systems integration.
        """,
        'context': """
            Parts orders complement aircraft orders and include maintenance, repair, and overhaul (MRO) activities. A healthy parts
            order book indicates both new production activity and sustained support for existing aircraft fleets. This metric can
            signal the health of the broader defense aerospace supply chain.
        """,
        'units': 'Millions of Dollars',
        'category': 'defense-industrial'
    },
    'ipb52300s': {
        'title': 'Industrial Production: Defense Equipment',
        'subtitle': 'Production output of defense and space equipment',
        'description': """
            The data set "Equipment: Defense and Space Equipment" measures how much the U.S. is producing in terms
            of military and space-related technology and machinery. Tracked monthly by the Federal Reserve, this index reflects the
            real output of U.S.-based manufacturers that build everything from weapons systems and armored vehicles to satellites
            and space launch components.
        """,
        'context': """
            By following this index, we get a clearer picture of the production capacity of the US defense industrial base. Rising
            production indicates manufacturers are actively building defense systems, while declining production may signal slower
            procurement or capacity constraints.
        """,
        'units': 'Index 2017=100',
        'category': 'defense-industrial'
    },
    'fdefx': {
        'title': 'National Defense Spending',
        'subtitle': 'Federal defense consumption expenditures and procurement',
        'description': """
            National Defense Consumption Expenditures (FDEFX) measures the total federal government spending
            on defense goods and services. This includes military personnel, operations, procurement of weapons systems,
            and research & development.
        """,
        'context': """
            This metric is a key indicator of defense budget trends and government commitment to defense priorities. Increases
            in defense spending often correlate with heightened geopolitical tensions, military modernization efforts, or shifts
            in strategic doctrine. It represents the actual dollars flowing into the defense sector.
        """,
        'units': 'Billions of Dollars',
        'category': 'defense-industrial'
    },
    'prmfgcons': {
        'title': 'Manufacturing Construction',
        'subtitle': 'Construction spending in the manufacturing sector',
        'description': """
            Manufacturing Construction Spending (PRMFGCONS) tracks expenditures on new manufacturing
            facilities, expansions, and renovations. This includes both defense-specific manufacturing facilities and
            the broader industrial base that supports defense production.
        """,
        'context': """
            Manufacturing construction is a leading indicator of future production capacity. Increased construction suggests
            businesses are preparing for higher output, which can include defense production. New facilities for semiconductors,
            advanced materials, or precision manufacturing directly support defense capabilities.
        """,
        'units': 'Millions of Dollars',
        'category': 'defense-industrial'
    },
    'ita': {
        'title': 'Aerospace & Defense ETF (ITA)',
        'subtitle': 'iShares U.S. Aerospace & Defense ETF investor sentiment',
        'description': """
            The iShares U.S. Aerospace & Defense ETF (ITA) tracks ETFs focused on the aerospace and defense
            sectors, reflecting investor sentiment. It is a basket of stocks of companies in the defense industrial base.
        """,
        'context': """
            Higher ITA prices demonstrate that investors believe the value of defense primes will increase, while lower prices
            suggest caution towards the growth of the defense industrial base. The ETF serves as a real-time measure of market
            confidence in the sector's future profitability and growth prospects.
        """,
        'units': 'Price (USD)',
        'category': 'defense-industrial'
    },
    'indpro': {
        'title': 'Industrial Production Index',
        'subtitle': 'Overall U.S. industrial production output',
        'description': """
            Industrial Production Index (INDPRO) measures the real output of manufacturing, mining, and
            electric and gas utilities industries. The index is benchmarked to 2017=100 and provides a broad measure of
            industrial activity across the entire U.S. economy.
        """,
        'context': """
            This broad measure reflects the overall health of U.S. industrial capacity, which is critical for defense
            manufacturing. Strong industrial production indicates a robust manufacturing base that can support defense
            contractors. It also signals the availability of skilled workers, supply chains, and industrial infrastructure.
        """,
        'units': 'Index 2017=100',
        'category': 'us-industrial'
    },
    'pnfi': {
        'title': 'Business Investment Trends',
        'subtitle': 'Private nonresidential fixed investment in structures and equipment',
        'description': """
            Private Nonresidential Fixed Investment (PNFI) measures business investment in structures, equipment,
            and intellectual property. This excludes residential construction and focuses on productive capital investments
            by businesses.
        """,
        'context': """
            Business investment is a key driver of economic growth and defense industrial capacity. Higher investment
            indicates businesses are expanding production capabilities, modernizing facilities, and investing in new
            technologies. These investments build the foundation for future defense manufacturing capacity.
        """,
        'units': 'Billions of Dollars',
        'category': 'us-industrial'
    },
    'gpdi': {
        'title': 'GDP Investment Component',
        'subtitle': 'Gross private domestic investment',
        'description': """
            Gross Private Domestic Investment (GPDI) measures business investment, residential
            investment, and changes in private inventories. This is a major component of GDP
            and represents the total investment activity in the economy.
        """,
        'context': """
            This component of GDP reflects overall investment activity in the economy. Strong investment indicates business
            confidence and capacity expansion, supporting defense industrial base growth. It captures the broader investment
            climate that enables or constrains defense manufacturing expansion.
        """,
        'units': 'Billions of Dollars',
        'category': 'us-industrial'
    },
    'drtscilm': {
        'title': 'Bank Lending Standards',
        'subtitle': 'Net percentage of banks tightening standards for commercial loans',
        'description': """
            Lending Standards (DRTSCILM) measures the net percentage of domestic banks reporting tightened
            lending standards for commercial and industrial loans. Positive values indicate tightening (harder to get loans),
            while negative values indicate loosening (easier to get loans).
        """,
        'context': """
            This metric is crucial for understanding credit availability to defense contractors and industrial companies.
            Tighter lending standards can constrain business expansion, capital expenditures, and working capital in the
            defense sector. Access to credit is essential for companies to take on large defense contracts and invest in
            new capabilities.
        """,
        'units': 'Percent',
        'category': 'us-industrial'
    },
    'xli': {
        'title': 'Industrial Sector ETF (XLI)',
        'subtitle': 'Industrial Select Sector SPDR Fund performance',
        'description': """
            XLI ETF tracks the Industrial sector of the S&P 500, including aerospace, defense,
            construction, engineering, machinery companies, and industrial conglomerates. It provides a broader view
            of industrial sector performance beyond just defense.
        """,
        'context': """
            XLI provides context for defense sector trends within the larger industrial economy. Strong XLI performance
            suggests robust demand for industrial products and services, healthy capital expenditures, and positive
            investor sentiment toward manufacturing and infrastructure. Defense contractors often benefit from the same
            economic tailwinds that lift the broader industrial sector.
        """,
        'units': 'Price (USD)',
        'category': 'us-industrial'
    },
    'pld': {
        'title': 'Prologis Inc. (PLD)',
        'subtitle': 'Industrial real estate REIT performance',
        'description': """
            Prologis (PLD) is the world's largest owner and operator of logistics real estate, including
            warehouses, distribution centers, and industrial facilities. Their properties support industrial and manufacturing
            activities across supply chains.
        """,
        'context': """
            PLD performance can indicate demand for industrial and logistics real estate, which supports defense manufacturing
            and supply chain operations. Rising PLD values suggest strong demand for industrial facilities, tight capacity,
            and growing manufacturing activity. This infrastructure is essential for defense contractors and their suppliers.
        """,
        'units': 'Price (USD)',
        'category': 'us-industrial'
    },
    'dgs10': {
        'title': '10-Year Treasury Yield',
        'subtitle': 'U.S. Treasury 10-year constant maturity rate',
        'description': """
            10-Year Treasury Yield (DGS10) is the yield on U.S. Treasury securities with a
            10-year maturity. This is a key benchmark interest rate that influences borrowing costs across the economy.
        """,
        'context': """
            Treasury yields affect borrowing costs for corporations and the government. Rising yields can increase
            financing costs for defense contractors, impacting their ability to invest in new capabilities and take on
            large contracts. Yields also reflect inflation expectations and economic growth projections, which influence
            defense budget planning and procurement decisions.
        """,
        'units': 'Percent',
        'category': 'us-industrial'
    }
}

def generate_navigation(active_page=None):
    """Generate navigation HTML"""
    active_attr = ' class="active"' if active_page == 'indicators' else ''
    nav_items = [
        '<li><a href="../index.html">Home</a></li>',
        '<li><a href="../deals/index.html">Deal Tracker</a></li>',
        f'<li><a href="../charts/indicators.html"{active_attr}>Indicators</a></li>',
    ]
    return '\n                '.join(nav_items)

def get_source_url(chart_id):
    """Get the source URL for a given chart"""
    # FRED series - use series ID from the chart_id (uppercase)
    fred_series = ['dgorder', 'fdefx', 'adefno', 'adapno', 'ipb52300s', 'prmfgcons',
                   'indpro', 'pnfi', 'gpdi', 'drtscilm', 'dgs10']

    # Yahoo Finance tickers - these don't have dedicated series pages
    yahoo_tickers = ['ita', 'xli', 'pld']

    # Custom data (no external source)
    custom_data = ['vc_defense', 'ma_defense', 'public_defense_companies']

    if chart_id in fred_series:
        # FRED URL format: https://fred.stlouisfed.org/series/{SERIES_ID}
        return f'https://fred.stlouisfed.org/series/{chart_id.upper()}'
    elif chart_id in yahoo_tickers:
        # Yahoo Finance ticker page
        return f'https://finance.yahoo.com/quote/{chart_id.upper()}'
    elif chart_id in custom_data:
        # No external source - custom research data
        return None
    else:
        return None


def get_source_name(chart_id):
    """Get the display source name for a chart"""
    fred_series = ['dgorder', 'fdefx', 'adefno', 'adapno', 'ipb52300s', 'prmfgcons',
                   'indpro', 'pnfi', 'gpdi', 'drtscilm', 'dgs10']
    yahoo_tickers = ['ita', 'xli', 'pld']
    if chart_id in fred_series:
        return 'Federal Reserve Economic Data (FRED)'
    elif chart_id in yahoo_tickers:
        return 'Yahoo Finance'
    else:
        return 'Custom Research'


def generate_indicators_page():
    """Generate the merged Defense Business Environment Indicators page"""

    nav_html = generate_navigation("indicators")

    # Build all sections
    sections_parts = []
    chart_scripts = []

    for cat_id, cat_info in CATEGORIES.items():
        insights_html = ''

        # Chart rows for this category
        chart_rows = []
        for cid in cat_info['charts']:
            if cid not in CHARTS:
                continue
            cinfo = CHARTS[cid]
            source_url = get_source_url(cid)
            source_name = get_source_name(cid)
            source_display = f'<a href="{source_url}" target="_blank" rel="noopener noreferrer">{source_name}</a>' if source_url else source_name
            desc = cinfo['description'].strip()
            chart_rows.append(f"""        <div class="indicators-row">
            <div class="indicators-chart-col is-loading">
                <div class="chart-loading">Loading…</div>
                <div class="chart-error">Data unavailable</div>
                <canvas id="chart_{cid}"></canvas>
            </div>
            <div class="indicators-desc-col">
                <h3>{cinfo['title']}</h3>
                <p class="indicators-subtitle">{cinfo['subtitle']}</p>
                <p>{desc}</p>
                <p class="indicators-source">Source: {source_display}</p>
            </div>
        </div>""")

            # Chart loading script for this chart
            is_limited = cid in ['public_defense_companies', 'vc_defense', 'ma_defense']
            chart_scripts.append(f"""            (function() {{
                const col = document.getElementById('chart_{cid}')?.parentElement;
                fetch('../data/{cid.lower()}.json')
                    .then(response => {{
                        if (!response.ok) throw new Error('HTTP ' + response.status);
                        return response.json();
                    }})
                    .then(data => {{
                        const ctx = document.getElementById('chart_{cid}');
                        if (!ctx || !data || !data.data) throw new Error('Missing data');
                        const limitedDataChart = {str(is_limited).lower()};
                        let displayData = data.data;
                        if (!limitedDataChart) {{
                            displayData = data.data.filter(d => new Date(d.date) >= new Date('{DEFAULT_START_DATE}'));
                        }}
                        const yearLabels = displayData.map(d => {{
                            const date = new Date(d.date);
                            return `${{date.getFullYear()}}`;
                        }});
                        new Chart(ctx, {{
                            type: 'line',
                            data: {{
                                labels: yearLabels,
                                datasets: [{{
                                    label: data.name,
                                    data: displayData.map(d => d.value || d.close),
                                    borderColor: '#1e456e',
                                    backgroundColor: 'rgba(93, 120, 144, 0.12)',
                                    borderWidth: 2,
                                    fill: true,
                                    tension: 0.1,
                                    pointRadius: 0
                                }}]
                            }},
                            options: {{
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {{ legend: {{ display: false }} }},
                                scales: {{
                                    x: {{
                                        display: true,
                                        grid: {{ display: true, color: '#e0e0e0' }},
                                        ticks: {{ maxRotation: 45, minRotation: 45, maxTicksLimit: 12 }}
                                    }},
                                    y: {{
                                        grid: {{ color: '#e0e0e0' }},
                                        beginAtZero: {str(cid in ['public_defense_companies', 'vc_defense', 'ma_defense', 'dgorder', 'fdefx', 'pnfi', 'gpdi', 'prmfgcons', 'adefno', 'adapno']).lower()},
                                        ticks: {{
                                            callback: function(value) {{
                                                const formats = {str(Y_AXIS_FORMATS.get(cid, {'prefix': '', 'suffix': '', 'divisor': 1}))};
                                                const displayValue = value / formats.divisor;
                                                return formats.prefix + displayValue.toLocaleString() + formats.suffix;
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }});
                        if (col) col.classList.remove('is-loading');
                    }})
                    .catch(err => {{
                        console.error('Could not load {cid}:', err);
                        if (col) {{ col.classList.remove('is-loading'); col.classList.add('is-error'); }}
                    }});
            }})();""")

        chart_rows_html = '\n'.join(chart_rows)
        sections_parts.append(f"""    <div class="indicators-section">
        <h2 class="indicators-section-header">{cat_info['title']}</h2>
{insights_html}
{chart_rows_html}
    </div>""")

    sections_html = '\n\n'.join(sections_parts)
    chart_scripts_html = '\n'.join(chart_scripts)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Defense Business Environment Indicators - Defense Capital Dashboard</title>
    <link rel="icon" type="image/svg+xml" href="../favicon.svg">
    <link rel="stylesheet" href="../css/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
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
                {nav_html}
            </ul>
        </div>
    </nav>

    <div class="page-header">
        <div class="page-header-inner">
            <p class="page-header-title">Selected indicators for the U.S. defense business environment</p>
            <p class="page-header-updated" id="indicatorsUpdated"></p>
        </div>
    </div>

    <div class="container">
{sections_html}
    </div>

    <footer>
        <p><strong>Defense Capital Dashboard</strong></p>
        <p>Data sources: Federal Reserve Economic Data (FRED), Yahoo Finance, Custom Research</p>
        <p style="font-size: 0.75rem; opacity: 0.7; margin-top: 0.5rem;">This product uses the FRED&reg; API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.</p>
        <p>Created by Sam Moyer | <a href="https://github.com/samuelmoyer91-sketch">GitHub</a></p>
    </footer>

    <script src="../js/main.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', async function() {{
            fetch('../data/dgs10.json')
                .then(r => r.json())
                .then(d => {{
                    if (d.last_updated) {{
                        document.getElementById('indicatorsUpdated').textContent = 'Last updated ' + d.last_updated;
                    }}
                }})
                .catch(() => {{}});
{chart_scripts_html}
        }});
    </script>
</body>
</html>"""

    return html



def generate_all_pages(output_dir=None):
    """Generate all chart and category pages"""

    if output_dir is None:
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent.parent / 'github_site' / 'charts'
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate indicators page
    html = generate_indicators_page()
    output_file = output_dir / 'indicators.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print("✓ Generated indicators.html")

if __name__ == '__main__':
    generate_all_pages()
