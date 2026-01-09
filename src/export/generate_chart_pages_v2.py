#!/usr/bin/env python3
"""
Generate HTML pages for all charts with reorganized navigation
Creates individual chart pages and category overview pages
"""

from pathlib import Path

# Navigation categories with key insights
CATEGORIES = {
    'defense-investment': {
        'title': 'Defense Investment Trends',
        'description': 'Tracking capital flows and investment activity in the defense sector',
        'charts': ['dgorder', 'public_defense_companies', 'vc_defense', 'ma_defense'],
        'insights': [
            'Defense capital goods orders provide early signals of future production activity and contractor revenue',
            'VC investment trends indicate emerging technology areas attracting private capital in defense',
            'M&A activity reflects industry consolidation and strategic positioning for major defense programs'
        ]
    },
    'defense-industrial': {
        'title': 'Defense Industrial Health',
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
        'title': 'Overall US Industrial Health',
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

# Chart definitions with user's original descriptions
CHARTS = {
    'dgorder': {
        'title': 'Defense Capital Goods Orders',
        'subtitle': "Manufacturers' new orders for defense capital goods",
        'description': """
            <strong>Manufacturers' New Orders: Defense Capital Goods</strong> is a data set released monthly by the US Census Bureau.
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
            <strong>Venture Capital Investment in Defense</strong> tracks the volume of venture capital dollars flowing into U.S.
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
            <strong>Public Defense Companies - Capex & R&D</strong> tracks the annual capital expenditures and research & development
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
            <strong>M&A Activity in Defense</strong> tracks the dollar value of mergers and acquisitions in the U.S. aerospace and
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
            <strong>Defense Aircraft Orders (ADEFNO)</strong> tracks new orders for complete military aircraft from manufacturers.
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
            <strong>Defense Aircraft Parts Orders (ADAPNO)</strong> measures orders for aircraft components, subassemblies, and
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
            The data set <strong>"Equipment: Defense and Space Equipment"</strong> measures how much the U.S. is producing in terms
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
            <strong>National Defense Consumption Expenditures (FDEFX)</strong> measures the total federal government spending
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
            <strong>Manufacturing Construction Spending (PRMFGCONS)</strong> tracks expenditures on new manufacturing
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
            The <strong>iShares U.S. Aerospace & Defense ETF (ITA)</strong> tracks ETFs focused on the aerospace and defense
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
            <strong>Industrial Production Index (INDPRO)</strong> measures the real output of manufacturing, mining, and
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
            <strong>Private Nonresidential Fixed Investment (PNFI)</strong> measures business investment in structures, equipment,
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
            <strong>Gross Private Domestic Investment (GPDI)</strong> measures business investment, residential
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
            <strong>Lending Standards (DRTSCILM)</strong> measures the net percentage of domestic banks reporting tightened
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
            <strong>XLI ETF</strong> tracks the Industrial sector of the S&P 500, including aerospace, defense,
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
            <strong>Prologis (PLD)</strong> is the world's largest owner and operator of logistics real estate, including
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
            <strong>10-Year Treasury Yield (DGS10)</strong> is the yield on U.S. Treasury securities with a
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

def generate_navigation(current_category=None):
    """Generate navigation HTML with category dropdowns"""

    nav_items = [
        '<li><a href="../index.html">Home</a></li>',
        '<li><a href="../deals/index.html">Deal Tracker</a></li>'
    ]

    for cat_id, cat_info in CATEGORIES.items():
        active = 'class="active"' if cat_id == current_category else ''
        nav_items.append(f'<li><a href="../charts/{cat_id}.html" {active}>{cat_info["title"]}</a></li>')

    return '\n                '.join(nav_items)

def generate_chart_page(chart_id, chart_info):
    """Generate HTML page for a single chart"""

    category = chart_info['category']
    nav_html = generate_navigation(category)

    # Determine if this is market data
    is_market = chart_id in ['ita', 'xli', 'pld', 'dgs10']
    data_file = f'../data/{chart_id.lower()}.json'

    # Find related charts in the same category
    related_charts = [cid for cid, cinfo in CHARTS.items()
                     if cinfo['category'] == category and cid != chart_id][:3]

    related_links = '\n                '.join([
        f'<a href="{get_chart_filename(cid)}" class="btn btn-secondary">{CHARTS[cid]["title"]}</a>'
        for cid in related_charts
    ])

    if not related_links:
        related_links = f'<a href="{category}.html" class="btn btn-secondary">Back to {CATEGORIES[category]["title"]}</a>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{chart_info['title']} - Defense Capital Dashboard</title>
    <link rel="stylesheet" href="../css/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
    <nav>
        <div class="container">
            <a href="../index.html" class="logo">Defense Capital Dashboard</a>
            <button class="mobile-menu-toggle">☰</button>
            <ul>
                {nav_html}
            </ul>
        </div>
    </nav>

    <div class="container">
        <div class="page-header">
            <h1>{chart_info['title']}</h1>
            <p>{chart_info['subtitle']}</p>
            <p class="last-updated" id="lastUpdated"></p>
        </div>

        <!-- Data Summary Stats -->
        <div class="data-summary" id="dataSummary" style="display: none;">
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-label">Latest Value</div>
                    <div class="summary-value" id="latestValue">--</div>
                    <div class="summary-change" id="latestDate">--</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Period Change</div>
                    <div class="summary-value" id="monthChange">--</div>
                    <div class="summary-change" id="monthChangePercent">--</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Year-over-Year</div>
                    <div class="summary-value" id="yearChange">--</div>
                    <div class="summary-change" id="yearChangePercent">--</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Trend</div>
                    <div class="summary-value"><span id="trendIndicator" class="trend-indicator">→</span></div>
                    <div class="summary-change">Recent direction</div>
                </div>
            </div>
        </div>

        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h2 style="margin: 0;">Chart</h2>
                <button class="btn btn-download" id="downloadBtn">Download CSV</button>
            </div>
            <div class="chart-container" style="height: 500px;">
                <canvas id="mainChart"></canvas>
            </div>
        </div>

        <div class="card">
            <h2>About This Metric</h2>
            <p>{chart_info['description']}</p>
            <p>{chart_info['context']}</p>
            <p><strong>Units:</strong> {chart_info['units']}</p>
            <p><strong>Source:</strong> {'Yahoo Finance' if is_market and chart_id != 'dgs10' else 'Federal Reserve Economic Data (FRED)'}</p>
        </div>

        <div class="card">
            <h2>Related Charts</h2>
            <div class="grid grid-3">
                {related_links}
            </div>
        </div>
    </div>

    <footer>
        <p>Defense Capital Dashboard</p>
        <p>Data source: {'Yahoo Finance' if is_market and chart_id != 'dgs10' else 'Federal Reserve Economic Data (FRED)'}</p>
    </footer>

    <script src="../js/main.js"></script>
    <script>
        let chartData = null;

        document.addEventListener('DOMContentLoaded', async function() {{
            try {{
                // Load data
                const response = await fetch('{data_file}');
                chartData = await response.json();

                // Calculate and display stats
                const stats = ChartUtils.calculateStats(chartData.data);
                if (stats) {{
                    document.getElementById('dataSummary').style.display = 'block';
                    document.getElementById('latestValue').textContent = ChartUtils.formatNumber(stats.latest.toFixed(2));
                    document.getElementById('latestDate').textContent = stats.latestDate;

                    if (stats.monthChange !== null) {{
                        const monthChangeElem = document.getElementById('monthChange');
                        const monthChangePercentElem = document.getElementById('monthChangePercent');
                        monthChangeElem.textContent = (stats.monthChange >= 0 ? '+' : '') + ChartUtils.formatNumber(stats.monthChange.toFixed(2));
                        monthChangePercentElem.textContent = (stats.monthChangePercent >= 0 ? '+' : '') + stats.monthChangePercent.toFixed(2) + '%';
                        monthChangePercentElem.className = 'summary-change ' + (stats.monthChangePercent > 0 ? 'positive' : stats.monthChangePercent < 0 ? 'negative' : 'neutral');
                    }}

                    const yearChangeElem = document.getElementById('yearChange');
                    const yearChangePercentElem = document.getElementById('yearChangePercent');
                    yearChangeElem.textContent = (stats.yearChange >= 0 ? '+' : '') + ChartUtils.formatNumber(stats.yearChange.toFixed(2));
                    yearChangePercentElem.textContent = (stats.yearChangePercent >= 0 ? '+' : '') + stats.yearChangePercent.toFixed(2) + '%';
                    yearChangePercentElem.className = 'summary-change ' + (stats.yearChangePercent > 0 ? 'positive' : stats.yearChangePercent < 0 ? 'negative' : 'neutral');

                    document.getElementById('trendIndicator').textContent = stats.trend;
                }}

                // Display last updated
                if (chartData.last_updated) {{
                    document.getElementById('lastUpdated').textContent = 'Last updated: ' + chartData.last_updated;
                }}

                // Filter data to 2019-present for consistent visualization
                // Exception: Annual investment charts (VC, M&A, PDC) show all available data
                const limitedDataCharts = ['public_defense_companies', 'vc_defense', 'ma_defense'];
                let displayData = chartData;

                if (!limitedDataCharts.includes('{chart_id}')) {{
                    const filteredData = chartData.data.filter(d => new Date(d.date) >= new Date('{DEFAULT_START_DATE}'));
                    if (filteredData.length > 0) {{
                        displayData = {{
                            ...chartData,
                            data: filteredData
                        }};
                    }}
                }}

                // Render chart with clean year-only labels
                const chartOptions = {{
                    fill: true,
                    scales: {{
                        x: {{
                            type: 'time',
                            time: {{
                                unit: 'year',
                                displayFormats: {{
                                    year: 'yyyy'
                                }}
                            }},
                            ticks: {{
                                maxTicksLimit: 10
                            }}
                        }},
                        y: {{
                            // Start at zero for investment/dollar amount charts
                            beginAtZero: ['public_defense_companies', 'vc_defense', 'ma_defense', 'dgorder', 'fdefx', 'pnfi', 'gpdi', 'prmfgcons', 'adefno', 'adapno'].includes('{chart_id}')
                        }}
                    }},
                    plugins: {{
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return `Value: ${{context.parsed.y.toFixed(2)}}`;
                                }}
                            }}
                        }}
                    }}
                }};

                ChartUtils.createLineChart('mainChart', displayData, chartOptions);
            }} catch (error) {{
                console.error('Error loading chart:', error);
            }}

            // Download button handler
            document.getElementById('downloadBtn').addEventListener('click', function() {{
                if (chartData) {{
                    ChartUtils.downloadCSV(chartData, '{chart_id}.csv');
                }}
            }});
        }});
    </script>
</body>
</html>"""

    return html

def generate_category_page(cat_id, cat_info):
    """Generate overview page for a category"""

    nav_html = generate_navigation(cat_id)

    # Get all charts in this category
    category_charts = [(cid, CHARTS[cid]) for cid in cat_info['charts'] if cid in CHARTS]

    # Generate chart cards
    chart_cards = []
    for cid, cinfo in category_charts:
        filename = get_chart_filename(cid)
        chart_cards.append(f"""
            <div class="card">
                <h3><a href="{filename}">{cinfo['title']}</a></h3>
                <p>{cinfo['subtitle']}</p>
                <div class="chart-container" style="height: 250px;">
                    <canvas id="chart_{cid}"></canvas>
                </div>
                <a href="{filename}" class="btn btn-primary" style="margin-top: 1rem;">View Details</a>
            </div>
        """)

    chart_cards_html = '\n            '.join(chart_cards)

    # Generate key insights HTML
    insights_html = ''
    if 'insights' in cat_info and cat_info['insights']:
        insights_items = '\n                    '.join([f'<li>{insight}</li>' for insight in cat_info['insights']])
        insights_html = f"""
        <div class="key-insights">
            <h3>Key Insights</h3>
            <ul>
                {insights_items}
            </ul>
        </div>"""

    # Generate chart loading scripts - using direct Chart.js to ensure all data shows
    chart_scripts = []
    for cid, cinfo in category_charts:
        chart_scripts.append(f"""
            fetch('../data/{cid.lower()}.json')
                .then(response => response.json())
                .then(data => {{
                    const ctx = document.getElementById('chart_{cid}');
                    if (!ctx) return;

                    // Show only recent data for cleaner previews (last 10 years)
                    const allData = data.data;
                    const recentData = allData.length > 120 ? allData.slice(-120) : allData;

                    new Chart(ctx, {{
                        type: 'line',
                        data: {{
                            labels: recentData.map(d => d.date),
                            datasets: [{{
                                label: data.name,
                                data: recentData.map(d => d.value || d.close),
                                borderColor: '#226E93',
                                backgroundColor: 'rgba(34, 110, 147, 0.1)',
                                borderWidth: 2,
                                fill: true,
                                tension: 0.1,
                                pointRadius: 0
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{ display: false }}
                            }},
                            scales: {{
                                x: {{ display: true, grid: {{ display: false }} }},
                                y: {{ grid: {{ color: '#e0e0e0' }} }}
                            }}
                        }}
                    }});
                }})
                .catch(err => console.log('Could not load {cid}:', err));
        """)

    chart_scripts_html = '\n            '.join(chart_scripts)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{cat_info['title']} - Defense Capital Dashboard</title>
    <link rel="stylesheet" href="../css/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
    <nav>
        <div class="container">
            <a href="../index.html" class="logo">Defense Capital Dashboard</a>
            <button class="mobile-menu-toggle">☰</button>
            <ul>
                {nav_html}
            </ul>
        </div>
    </nav>

    <div class="container">
        <div class="page-header">
            <h1>{cat_info['title']}</h1>
            <p>{cat_info['description']}</p>
        </div>

        {insights_html}

        <div class="grid grid-2">
            {chart_cards_html}
        </div>
    </div>

    <footer>
        <p>Defense Capital Dashboard</p>
        <p>Data sources: Federal Reserve Economic Data (FRED), Yahoo Finance</p>
    </footer>

    <script src="../js/main.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', async function() {{
            {chart_scripts_html}
        }});
    </script>
</body>
</html>"""

    return html

def get_chart_filename(chart_id):
    """Get the HTML filename for a chart"""
    filename_map = {
        'fdefx': 'defense-spending.html',
        'drtscilm': 'lending-standards.html',
        'dgorder': 'defense-goods-orders.html',
        'indpro': 'industrial-production.html',
        'pnfi': 'investment-trends.html',
        'adefno': 'aircraft-orders.html',
        'adapno': 'aircraft-parts-orders.html',
        'gpdi': 'gdp-investment.html',
        'prmfgcons': 'manufacturing-construction.html',
        'ipb52300s': 'manufacturing-production.html',
        'ita': 'ita.html',
        'xli': 'xli.html',
        'pld': 'pld.html',
        'dgs10': 'dgs10.html',
        'public_defense_companies': 'public-defense-companies.html',
        'vc_defense': 'vc-investment.html',
        'ma_defense': 'ma-activity.html'
    }
    return filename_map.get(chart_id, f'{chart_id}.html')

def generate_all_pages(output_dir=None):
    """Generate all chart and category pages"""

    if output_dir is None:
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent.parent / 'github_site' / 'charts'
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate individual chart pages
    for chart_id, chart_info in CHARTS.items():
        html = generate_chart_page(chart_id, chart_info)
        filename = get_chart_filename(chart_id)
        output_file = output_dir / filename
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✓ Generated {filename}")

    # Generate category overview pages
    for cat_id, cat_info in CATEGORIES.items():
        html = generate_category_page(cat_id, cat_info)
        output_file = output_dir / f'{cat_id}.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✓ Generated {cat_id}.html (category page)")

    print(f"\n✓ Generated {len(CHARTS)} chart pages + {len(CATEGORIES)} category pages")

if __name__ == '__main__':
    generate_all_pages()
