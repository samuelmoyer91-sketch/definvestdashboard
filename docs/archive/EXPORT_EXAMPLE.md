# What Your Exported Data Looks Like

## CSV Export Format

When you run the export, you'll get a CSV file with these columns:

| Date | Company | Investment Amount | Capital Type | Sector | Location | Project Type | Summary | Source URL |
|------|---------|-------------------|--------------|--------|----------|--------------|---------|------------|

## Example Data (from your current master list)

| Date | Company | Investment Amount | Capital Type | Sector | Location | Project Type | Summary | Source URL |
|------|---------|-------------------|--------------|--------|----------|--------------|---------|------------|
| 2026-01-02 | McNally Capital | Not disclosed | Private Equity | Aerospace | Austin TX | Acquisition | McNally Capital, a private equity firm specializing in mid-market aerospace and defense, acquired ATS, a PT6A MRO specialist | [Link] |

## When You Have More Data (Example)

Here's what it could look like with 10+ curated deals:

| Date | Company | Investment Amount | Capital Type | Sector | Location | Project Type | Summary | Source URL |
|------|---------|-------------------|--------------|--------|----------|--------------|---------|------------|
| 2026-01-05 | Anduril Industries | $1.5B | Venture Capital | Drones | California | Funding Round | Series F funding for autonomous defense systems and AI-powered surveillance | [Link] |
| 2026-01-04 | Shield AI | $500M | Venture Capital | AI/ML | San Diego, CA | Funding Round | Series E funding to scale production of Hivemind AI pilot technology | [Link] |
| 2026-01-03 | Palantir Technologies | $300M | Public-Private | Software | Colorado | Contract Award | Multi-year contract for data analytics platform supporting DoD operations | [Link] |
| 2026-01-02 | McNally Capital | Not disclosed | Private Equity | Aerospace | Austin, TX | Acquisition | Acquired ATS, PT6A engine MRO specialist serving defense aviation sector | [Link] |
| 2025-12-28 | General Atomics | $2.1B | Corporate | Drones | California | Factory | Construction of new manufacturing facility for MQ-9 Reaper production expansion | [Link] |
| 2025-12-20 | Northrop Grumman | Not disclosed | Corporate | Semiconductors | Arizona | Factory | Partnership with TSMC for defense-grade chip manufacturing facility | [Link] |
| 2025-12-15 | Lockheed Martin Ventures | $150M | Corporate VC | Space | Multiple | Fund Launch | New fund targeting dual-use space technology startups | [Link] |
| 2025-12-10 | AE Industrial Partners | $800M | Private Equity | Manufacturing | Ohio | Acquisition | Acquired aerospace components manufacturer supporting F-35 supply chain | [Link] |

## How It Will Look on Your Google Site

When embedded on your Google Sites page, it will appear as:
- **Scrollable table** (users can scroll down to see all deals)
- **Sortable** (click column headers to sort)
- **Searchable** (Ctrl+F works)
- **Responsive** (adjusts to mobile/tablet)

### Formatting Tips for Google Sheets

To make it look professional:

1. **Header row:** Bold, colored background (match your site's teal theme)
2. **Freeze header:** So it stays visible when scrolling
3. **Column widths:**
   - Date: Narrow (80-100px)
   - Company: Medium (150px)
   - Investment Amount: Medium (120px)
   - Capital Type: Narrow (100px)
   - Sector: Medium (120px)
   - Location: Medium (120px)
   - Project Type: Medium (120px)
   - Summary: Wide (300-400px)
   - Source URL: Hide or narrow (users can click if you make it a hyperlink)

4. **Conditional formatting** (optional but cool):
   - Highlight "Venture Capital" rows in light blue
   - Highlight "Private Equity" rows in light green
   - Highlight investments >$1B in bold

5. **Add a filter row:**
   - Data → Create a filter
   - Users can filter by sector, capital type, etc.

## Future Enhancements

Once you have 50+ deals, you can add:

### Summary Statistics (top of page)
- **Total Capital Tracked:** $8.5B
- **Number of Deals:** 52
- **Top Sector:** Drones (18 deals)
- **Last Updated:** Jan 3, 2026

### Charts (separate embeds)
- **Deals by Sector** (pie chart)
- **Investment Over Time** (line chart)
- **Capital Type Breakdown** (bar chart)
- **Geographic Distribution** (map or bar chart)

### Multiple Views
Create separate sheets in the same Google Sheet file:
- **All Deals** (complete list)
- **2024 Deals** (filtered by year)
- **Major Deals** (>$100M only)
- **VC Deals** (venture capital only)
- **PE Deals** (private equity only)

Embed different sheets on different pages of your site!

## Comparison to Your Other Dashboards

Your existing pages show **time-series macro data** (Fed indicators, ETFs, spending over time).

This new page shows **deal-level microdata** (individual investments, companies, projects).

Together, they create a **complete picture**:
- **Macro:** Is defense capital increasing overall? (Your existing charts)
- **Micro:** Where specifically is that capital going? (Your new deal tracker)

This is powerful for:
- **Investors:** See specific deals and trends
- **Analysts:** Track which sectors are hot
- **Job seekers:** Identify growing companies
- **Researchers:** Export data for analysis

## Export File Location

After running the export:
```
~/Documents/Claude - Defense PC Dashboard/exports/master_list.csv
```

This file updates every time you run the export, always reflecting your latest master list.
