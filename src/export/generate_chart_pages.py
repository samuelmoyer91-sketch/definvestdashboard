#!/usr/bin/env python3
"""
Generate HTML pages for all FRED charts
Creates individual chart pages from template
"""

from pathlib import Path

# Chart definitions
CHARTS = {
    'fdefx': {
        'title': 'National Defense Spending',
        'subtitle': 'Federal defense consumption expenditures and procurement trends',
        'description': """
            <strong>National Defense Consumption Expenditures (FDEFX)</strong> measures the total federal government spending
            on defense goods and services. This includes military personnel, operations, procurement of weapons systems,
            and research & development.
        """,
        'context': """
            This metric is a key indicator of defense budget trends and government commitment to defense priorities.
            Increases in defense spending often correlate with heightened geopolitical tensions or military modernization efforts.
        """,
        'units': 'Billions of Dollars',
        'related': ['defense-goods-orders', 'aircraft-orders', 'industrial-production']
    },
    'drtscilm': {
        'title': 'Bank Lending Standards',
        'subtitle': 'Net percentage of banks tightening standards for commercial loans',
        'description': """
            <strong>Lending Standards (DRTSCILM)</strong> measures the net percentage of domestic banks reporting tightened
            lending standards for commercial and industrial loans. Positive values indicate tightening, negative values
            indicate loosening.
        """,
        'context': """
            This metric is crucial for understanding credit availability to defense contractors and industrial companies.
            Tighter lending standards can constrain business expansion and capital expenditures in the defense sector.
        """,
        'units': 'Percent',
        'related': ['investment-trends', 'industrial-production', 'manufacturing-construction']
    },
    'dgorder': {
        'title': 'Defense Goods Orders',
        'subtitle': "Manufacturers' new orders for durable goods in the defense sector",
        'description': """
            <strong>Defense Goods Orders (DGORDER)</strong> tracks new orders received by manufacturers for defense-related
            durable goods. This is a leading indicator of future defense production activity.
        """,
        'context': """
            Rising orders suggest increased demand for defense products and can indicate upcoming production increases.
            This metric often leads actual defense spending by several months.
        """,
        'units': 'Millions of Dollars',
        'related': ['defense-spending', 'aircraft-orders', 'industrial-production']
    },
    'indpro': {
        'title': 'Industrial Production Index',
        'subtitle': 'Overall U.S. industrial production output',
        'description': """
            <strong>Industrial Production Index (INDPRO)</strong> measures the real output of manufacturing, mining, and
            electric and gas utilities industries. The index is benchmarked to 2017=100.
        """,
        'context': """
            This broad measure reflects the overall health of U.S. industrial capacity, which is critical for defense
            manufacturing. Strong industrial production indicates a robust manufacturing base for defense contractors.
        """,
        'units': 'Index 2017=100',
        'related': ['manufacturing-construction', 'investment-trends', 'defense-goods-orders']
    },
    'nfi': {
        'title': 'Business Investment Trends',
        'subtitle': 'Nonresidential fixed investment in structures and equipment',
        'description': """
            <strong>Nonresidential Fixed Investment (NFI)</strong> measures business investment in structures, equipment,
            and intellectual property. This excludes residential construction.
        """,
        'context': """
            Business investment is a key driver of economic growth and defense industrial capacity. Higher investment
            indicates businesses are expanding production capabilities and modernizing facilities.
        """,
        'units': 'Billions of Dollars',
        'related': ['industrial-production', 'manufacturing-construction', 'lending-standards']
    },
    'adefno': {
        'title': 'Defense Aircraft Orders',
        'subtitle': "Manufacturers' new orders for defense aircraft",
        'description': """
            <strong>Defense Aircraft Orders (ADEFNO)</strong> tracks new orders for military aircraft from manufacturers.
            This is a key indicator for the aerospace and defense sector.
        """,
        'context': """
            Aircraft orders are often large, multi-year contracts that provide visibility into future aerospace sector
            performance. Major programs like fighter jets and transport aircraft drive significant economic activity.
        """,
        'units': 'Millions of Dollars',
        'related': ['aircraft-parts-orders', 'defense-goods-orders', 'defense-spending']
    },
    'adapno': {
        'title': 'Defense Aircraft Parts Orders',
        'subtitle': "Manufacturers' new orders for defense aircraft parts and components",
        'description': """
            <strong>Defense Aircraft Parts Orders (ADAPNO)</strong> measures orders for aircraft parts, components, and
            subassemblies used in defense applications.
        """,
        'context': """
            Parts orders complement aircraft orders and include maintenance, repair, and overhaul (MRO) activities.
            This metric reflects both new production and support for existing aircraft fleets.
        """,
        'units': 'Millions of Dollars',
        'related': ['aircraft-orders', 'defense-goods-orders', 'industrial-production']
    },
    'gdpic1': {
        'title': 'GDP Investment Component',
        'subtitle': 'Real gross private domestic investment',
        'description': """
            <strong>Real Gross Private Domestic Investment (GDPIC1)</strong> measures business investment, residential
            investment, and changes in private inventories, adjusted for inflation.
        """,
        'context': """
            This component of GDP reflects overall investment activity in the economy. Strong investment indicates business
            confidence and capacity expansion, supporting defense industrial base growth.
        """,
        'units': 'Billions of Chained 2017 Dollars',
        'related': ['investment-trends', 'industrial-production', 'manufacturing-construction']
    },
    'prmfgcons': {
        'title': 'Manufacturing Construction',
        'subtitle': 'Construction spending in the manufacturing sector',
        'description': """
            <strong>Manufacturing Construction Spending (PRMFGCONS)</strong> tracks expenditures on new manufacturing
            facilities, expansions, and renovations.
        """,
        'context': """
            Manufacturing construction is a leading indicator of future production capacity. Increased construction suggests
            businesses are preparing for higher output, which can include defense production.
        """,
        'units': 'Millions of Dollars',
        'related': ['investment-trends', 'industrial-production', 'lending-standards']
    },
    'ipb52300s': {
        'title': 'Manufacturing Production Index',
        'subtitle': 'Industrial production metric for manufacturing sector (SIC)',
        'description': """
            <strong>Industrial Production: Manufacturing (IPB52300S)</strong> measures output in the manufacturing sector
            using Standard Industrial Classification (SIC) methodology.
        """,
        'context': """
            This metric provides a detailed view of manufacturing sector performance, which is critical for defense
            production. Strong manufacturing output supports defense industrial capacity.
        """,
        'units': 'Index 2017=100',
        'related': ['industrial-production', 'manufacturing-construction', 'defense-goods-orders']
    }
}

# Stock/ETF charts
MARKET_CHARTS = {
    'ita': {
        'title': 'Aerospace & Defense ETF (ITA)',
        'subtitle': 'iShares U.S. Aerospace & Defense ETF performance',
        'description': """
            <strong>ITA ETF</strong> tracks the performance of U.S. aerospace and defense companies. Holdings include
            major defense contractors, aerospace manufacturers, and related suppliers.
        """,
        'context': """
            ITA performance reflects investor sentiment toward the defense sector and can indicate expectations for
            future defense spending and contract awards.
        """,
        'units': 'Price (USD)',
        'related': ['xli', 'market-overview']
    },
    'xli': {
        'title': 'Industrial Sector ETF (XLI)',
        'subtitle': 'Industrial Select Sector SPDR Fund performance',
        'description': """
            <strong>XLI ETF</strong> tracks the Industrial sector of the S&P 500, including aerospace, defense,
            construction, engineering, and machinery companies.
        """,
        'context': """
            XLI provides a broader view of industrial sector performance, offering context for defense sector trends
            within the larger industrial economy.
        """,
        'units': 'Price (USD)',
        'related': ['ita', 'market-overview']
    },
    'pld': {
        'title': 'Prologis Inc. (PLD)',
        'subtitle': 'Industrial real estate REIT performance',
        'description': """
            <strong>Prologis (PLD)</strong> is the world's largest owner and operator of logistics real estate.
            Their facilities support industrial and manufacturing activities.
        """,
        'context': """
            PLD performance can indicate demand for industrial and logistics real estate, which supports
            defense manufacturing and supply chain operations.
        """,
        'units': 'Price (USD)',
        'related': ['xli', 'market-overview']
    },
    'dgs10': {
        'title': '10-Year Treasury Yield',
        'subtitle': 'U.S. Treasury 10-year constant maturity rate',
        'description': """
            <strong>10-Year Treasury Yield (DGS10)</strong> is the yield on U.S. Treasury securities with a
            10-year maturity. This is a key benchmark interest rate.
        """,
        'context': """
            Treasury yields affect borrowing costs for corporations and the government. Rising yields can increase
            financing costs for defense contractors and impact capital allocation decisions.
        """,
        'units': 'Percent',
        'related': ['lending-standards', 'investment-trends']
    }
}

def generate_chart_page(chart_id, chart_info, is_market=False):
    """Generate HTML page for a single chart"""

    related_links = '\n                '.join([
        f'<a href="{r}.html" class="btn btn-secondary">{r.replace("-", " ").title()}</a>'
        for r in chart_info['related'][:3]
    ])

    data_file = f'../data/{chart_id.lower()}.json'
    tooltip_format = 'close' if is_market else 'value'
    tooltip_label = '$${context.parsed.y.toFixed(2)}' if is_market else 'context.parsed.y.toFixed(1)'

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
                <li><a href="../index.html">Home</a></li>
                <li><a href="../deals/index.html">Deal Tracker</a></li>
                <li><a href="defense-spending.html" class="active">Charts</a></li>
            </ul>
        </div>
    </nav>

    <div class="container">
        <div class="page-header">
            <h1>{chart_info['title']}</h1>
            <p>{chart_info['subtitle']}</p>
        </div>

        <div class="card">
            <div class="chart-container" style="height: 500px;">
                <canvas id="mainChart"></canvas>
            </div>
        </div>

        <div class="card">
            <h2>About This Metric</h2>
            <p>{chart_info['description']}</p>
            <p>{chart_info['context']}</p>
            <p><strong>Units:</strong> {chart_info['units']}</p>
            <p><strong>Source:</strong> {'Yahoo Finance' if is_market and chart_id.upper() != 'DGS10' else 'Federal Reserve Economic Data (FRED)'}</p>
            <p id="lastUpdated" style="color: #666; font-size: 0.9rem;"></p>
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
        <p>Data source: {'Yahoo Finance / FRED' if is_market else 'Federal Reserve Economic Data (FRED)'}</p>
    </footer>

    <script src="../js/main.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', async function() {{
            await ChartUtils.loadAndRenderChart(
                '{data_file}',
                'mainChart',
                {{
                    fill: true,
                    plugins: {{
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return `{chart_info['units'].split()[0]}: ${{context.parsed.y.toFixed(2)}}`;
                                }}
                            }}
                        }}
                    }}
                }}
            );
        }});
    </script>
</body>
</html>"""

    return html

def generate_market_overview():
    """Generate market overview page comparing all market instruments"""

    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market Overview - Defense Capital Dashboard</title>
    <link rel="stylesheet" href="../css/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
    <nav>
        <div class="container">
            <a href="../index.html" class="logo">Defense Capital Dashboard</a>
            <button class="mobile-menu-toggle">☰</button>
            <ul>
                <li><a href="../index.html">Home</a></li>
                <li><a href="../deals/index.html">Deal Tracker</a></li>
                <li><a href="defense-spending.html" class="active">Charts</a></li>
            </ul>
        </div>
    </nav>

    <div class="container">
        <div class="page-header">
            <h1>Market Overview</h1>
            <p>Defense and industrial sector market performance</p>
        </div>

        <div class="card">
            <h2>Sector Comparison</h2>
            <div class="chart-container" style="height: 500px;">
                <canvas id="comparisonChart"></canvas>
            </div>
        </div>

        <div class="grid grid-2">
            <div class="card">
                <h3>Aerospace & Defense ETF (ITA)</h3>
                <div class="chart-container" style="height: 300px;">
                    <canvas id="itaChart"></canvas>
                </div>
            </div>

            <div class="card">
                <h3>Industrial Sector ETF (XLI)</h3>
                <div class="chart-container" style="height: 300px;">
                    <canvas id="xliChart"></canvas>
                </div>
            </div>

            <div class="card">
                <h3>Prologis Inc. (PLD)</h3>
                <div class="chart-container" style="height: 300px;">
                    <canvas id="pldChart"></canvas>
                </div>
            </div>

            <div class="card">
                <h3>10-Year Treasury Yield</h3>
                <div class="chart-container" style="height: 300px;">
                    <canvas id="dgs10Chart"></canvas>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>About These Metrics</h2>
            <p>
                This page provides a comprehensive view of market performance across defense, industrial, and related sectors.
                Tracking these instruments together helps identify broader trends and correlations.
            </p>
        </div>
    </div>

    <footer>
        <p>Defense Capital Dashboard</p>
        <p>Data sources: Yahoo Finance, Federal Reserve Economic Data (FRED)</p>
    </footer>

    <script src="../js/main.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', async function() {
            // Load individual charts
            ChartUtils.loadAndRenderChart('../data/ita.json', 'itaChart', { fill: true });
            ChartUtils.loadAndRenderChart('../data/xli.json', 'xliChart', { fill: true });
            ChartUtils.loadAndRenderChart('../data/pld.json', 'pldChart', { fill: true });
            ChartUtils.loadAndRenderChart('../data/dgs10.json', 'dgs10Chart', { fill: true });

            // Load comparison chart
            ChartUtils.loadAndRenderMultiChart(
                ['../data/ita.json', '../data/xli.json', '../data/pld.json'],
                'comparisonChart'
            );
        });
    </script>
</body>
</html>"""

    return html

def generate_all_chart_pages(output_dir=None):
    """Generate all chart pages"""

    if output_dir is None:
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent.parent / 'github_site' / 'charts'
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate FRED chart pages
    for chart_id, chart_info in CHARTS.items():
        html = generate_chart_page(chart_id, chart_info, is_market=False)
        filename = chart_id.replace('_', '-') + '.html'

        # Create friendly filename
        if chart_id == 'fdefx':
            filename = 'defense-spending.html'
        elif chart_id == 'drtscilm':
            filename = 'lending-standards.html'
        elif chart_id == 'dgorder':
            filename = 'defense-goods-orders.html'
        elif chart_id == 'indpro':
            filename = 'industrial-production.html'
        elif chart_id == 'nfi':
            filename = 'investment-trends.html'
        elif chart_id == 'adefno':
            filename = 'aircraft-orders.html'
        elif chart_id == 'adapno':
            filename = 'aircraft-parts-orders.html'
        elif chart_id == 'gdpic1':
            filename = 'gdp-investment.html'
        elif chart_id == 'prmfgcons':
            filename = 'manufacturing-construction.html'
        elif chart_id == 'ipb52300s':
            filename = 'manufacturing-production.html'

        output_file = output_dir / filename
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✓ Generated {filename}")

    # Generate market chart pages
    for chart_id, chart_info in MARKET_CHARTS.items():
        html = generate_chart_page(chart_id, chart_info, is_market=True)
        filename = chart_id.lower() + '.html'
        output_file = output_dir / filename
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✓ Generated {filename}")

    # Generate market overview page
    market_overview_html = generate_market_overview()
    with open(output_dir / 'market-overview.html', 'w', encoding='utf-8') as f:
        f.write(market_overview_html)
    print(f"✓ Generated market-overview.html")

    print(f"\n✓ Generated {len(CHARTS) + len(MARKET_CHARTS) + 1} chart pages")

if __name__ == '__main__':
    generate_all_chart_pages()
