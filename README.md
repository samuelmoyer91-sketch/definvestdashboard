# Defense Capital Dashboard

A professional dashboard tracking defense sector investments, industrial health, and economic indicators - designed for defense analysts, think tankers, and industry researchers.

**[🔗 View Live Dashboard](https://samuelmoyer91-sketch.github.io/definvestdashboard/)**

---

## 📊 Overview

This dashboard provides comprehensive visibility into the defense industrial base and capital markets:

### Three Core Categories:

1. **Defense Investment Trends** - Capital flows and funding activity
   - Defense capital goods orders
   - Venture capital investment in defense tech
   - M&A activity in aerospace & defense

2. **Defense Industrial Health** - Production capacity and contractor activity
   - Aircraft and equipment manufacturing
   - Defense spending and procurement
   - Manufacturing construction

3. **Overall US Industrial Health** - Broader economic context
   - Industrial production indices
   - Business investment trends
   - Lending standards and interest rates

---

## ✨ Professional Features

### Analyst-Focused Tools:
- **📈 Data Summary Stats** - Latest values, period changes, YoY trends with visual indicators
- **⬇️ CSV Export** - One-click download of economic/market datasets for custom analysis
- **🔍 Key Insights** - Curated context explaining metric relationships
- **📅 Timestamps** - Data freshness displayed on every page
- **📱 Mobile Responsive** - Professional design on all devices
- **🤖 AI Drafting Assistant** - Claude pre-populates triage form (you review/edit before publishing)

### Interactive Charts:
- Hover for exact values with formatted units ($B, $T, %)
- Clean quarterly labels (2019 Q1, 2020 Q2, etc.)
- Consistent 2019-present timeframe across all charts
- Vertical gridlines marking quarters and years
- Properly scaled y-axes (billions, trillions, percentages)
- Full historical data available via CSV export (for economic/market data only)

### Intelligence Briefing Deal Feed:
- Professional briefing-style layout for government analysts
- 100% human-curated content (AI assists but never publishes directly)
- Clean text-based visual hierarchy:
  - Transaction type and date in header
  - Company name prominent (1.4rem, bold)
  - Labeled metadata fields (Amount, Investors, Capital, Sectors)
  - Labels uppercase/light gray, values dark/medium weight
  - Fields only show when data exists (graceful degradation)
- Enhanced category system:
  - **Transaction Type**: Equity Funding Round, Acquisition, Merger, Contract/Award, Joint Venture, Internal Investment, etc.
  - **Capital Sources**: Venture Capital, Corporate Venture, Private Equity, Government/Contract, Public Markets, etc. (multi-select)
  - **Sectors**: AI/ML, Autonomous Systems/Drones, Space/Satellites, Aerospace, Cybersecurity, etc. (multi-select)
- AI pre-populates triage form with deal details and draft summaries
- You review and edit everything before publication
- Published dashboard shows only your curated content (never raw AI or RSS data)
- Source attribution on every article link
- Real-time search and filtering by transaction type
- Chronological feed with pagination

---

## 🎯 Use Cases

**Defense Analysts**: Export data for policy papers, cite latest values with timestamps

**Think Tank Researchers**: Download datasets for custom modeling and analysis

**Industry Associations**: Use key insights as talking points for board presentations

**Journalists**: Access data for investigative reporting on defense sector trends

**Academics**: Import data into statistical models for research

---

## 📊 Data Sources

- **FRED API** - 10 Federal Reserve economic series
- **Yahoo Finance** - Defense ETFs (ITA), industrials (XLI), REITs (PLD), Treasuries (DGS10)
- **Custom Research** - VC/M&A data from defense sector tracking
- **RSS Feeds** - Curated M&A deal announcements (private tool)

---

## 🛠️ Technology Stack

### Frontend:
- **Chart.js 4.4.0** - Interactive visualizations
- **Vanilla JavaScript** - No heavy frameworks, fast loading
- **Responsive CSS** - Mobile-first design with teal theme (#226E93)
- **Static HTML** - No server required, CDN-backed

### Backend (Data Pipeline):
- **Python 3** - Data fetching and page generation
- **fredapi** - Official FRED API client
- **yfinance** - Yahoo Finance data
- **pandas** - Excel data processing
- **SQLite** - Deal curation database (local)
- **FastAPI** - Local triage UI for deal curation
- **Claude AI (Anthropic)** - AI-powered deal analysis and summaries

### Hosting:
- **GitHub Pages** - Free, fast, reliable
- **Git Version Control** - Full change history
- **Automated Deployment** - Push to update in 30 seconds

---

## 🔄 Weekly Update Workflow

### ⭐ Recommended: Complete Update with New Deals

Use the automated workflow script for the full process:

```bash
cd ~/Documents/Claude/"Claude - Defense PC Dashboard"

# Step 1: Fetch and prepare data (automated - 2 min)
./update_workflow.sh all
# Fetches RSS → scrapes articles → generates AI summaries
# Then pauses for your manual triage

# Step 2: Manual triage (10-15 min)
uvicorn src.web.app:app --reload
# Open http://127.0.0.1:8000
# Review AI-populated deals with collapsible cards
# Edit company names, amounts, investors, categories, and summaries
# Accept curated deals (what you approve is what publishes)
# Reject irrelevant articles

# Step 3: Publish and deploy (automated - 1 min)
./update_workflow.sh publish
# Refreshes ALL data (FRED, Yahoo Finance)
# Generates website with new deals
# Auto-commits and deploys to GitHub Pages
```

**Total time: ~15 minutes** (vs. 2-3 hours manual)

---

### Quick Data Update (Charts Only, No New Deals)

**Note:** The automated workflow (`./update_workflow.sh publish`) is recommended as it refreshes all data automatically. Manual updates below are for advanced use only.

```bash
# Manual update (if workflow script unavailable)
cd ~/Documents/Claude/"Claude - Defense PC Dashboard"
python3 generate_site.py
git add github_site/
git commit -m "Data update - $(date +%Y-%m-%d)"
git push origin main
git subtree push --prefix github_site origin gh-pages
```

**Time required:** 2 minutes

**See [docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md) for detailed AI setup instructions.**

---

## 📁 Project Structure

```
Claude - Defense PC Dashboard/
├── github_site/              # Published website (deployed to GitHub Pages)
│   ├── index.html           # Homepage
│   ├── charts/              # 16 individual chart pages + 3 category pages
│   ├── deals/               # Deal tracker (intelligence briefing style)
│   ├── data/                # JSON datasets (FRED, finance, custom)
│   ├── css/                 # Styling (includes briefing styles)
│   └── js/                  # Chart utilities
├── src/
│   ├── data_fetchers/       # FRED, Yahoo Finance, Excel extractors
│   ├── export/              # HTML generators (chart pages, deal feed)
│   ├── scraper/             # RSS fetcher, article scraper, AI summarizer
│   ├── utils/               # AI summarizer (Claude API)
│   ├── web/                 # Local triage UI (FastAPI)
│   └── database/            # SQLite models (includes AIExtraction)
├── databases/               # SQLite databases (local only, not deployed)
│   ├── tracker.db           # Deal curation database
│   └── defense_deals.db     # Legacy database
├── data/                    # Source data (JSON files for charts)
├── docs/
│   └── AI_WORKFLOW.md       # AI summary setup and usage guide
├── *.xlsx                   # Excel source files (VC/M&A data)
├── generate_site.py         # Site generation script (data + HTML)
└── requirements.txt         # Python dependencies (includes anthropic)
```

---

## 🚀 Setup (For Maintenance)

### Prerequisites:
```bash
# Install dependencies
pip3 install -r requirements.txt

# Set FRED API key (get free key from fred.stlouisfed.org)
echo "export FRED_API_KEY='your_key_here'" >> ~/.zshrc
source ~/.zshrc
```

### Run Locally:
```bash
cd github_site
python3 -m http.server 8080
# Open http://localhost:8080
```

### Generate Site:
```bash
python3 generate_site.py
```

---

## 📈 What Gets Updated Weekly

- **Economic Indicators** - Latest FRED data (monthly releases)
- **Market Prices** - Current ETF/stock prices
- **Deal Tracker** - Newly curated M&A announcements
- **Chart Pages** - Regenerated with fresh data
- **Summary Statistics** - Auto-calculated from new data

---

## 🎨 Design Philosophy

**Analyst-First**: Every feature answers "What would a defense analyst need?"

**Data Transparency**: Timestamps, sources, export capability

**Professional Quality**: Clean design, reliable hosting, version control

**Simple Maintenance**: One command to update, push to deploy

**No Vendor Lock-In**: Static files, open standards, portable anywhere

---

## 📝 Documentation

- **IMPROVEMENTS_SUMMARY.md** - Details on professional features (stats, export, insights)
- **REVIEW_INSTRUCTIONS.md** - Testing and deployment guide
- **QUICK_REFERENCE.md** - Common commands cheat sheet

---

## 🔐 Privacy & Security

- Main dashboard is public (for portfolio/sharing)
- Deal triage tool runs locally (not on internet)
- Database with curated deals stays on your computer
- RSS feeds and raw articles processed locally
- Only approved deals exported to public site
- AI-generated drafts never appear in published output (only human-curated content)

---

## 🏆 Portfolio Highlights

**Technical Skills Demonstrated:**
- Static site generation with Python
- Data pipeline automation (APIs, Excel, databases)
- Interactive data visualization (Chart.js)
- Responsive web design (mobile-first CSS)
- Git version control with feature branches
- Professional analyst tool design
- Clean, maintainable code architecture

**Domain Knowledge:**
- Defense industrial base metrics
- Economic indicators and their relationships
- Capital markets (VC, M&A, public equities)
- Data analysis and presentation

---

## 📞 Contact

**Sam Moyer**
- GitHub: [@samuelmoyer91-sketch](https://github.com/samuelmoyer91-sketch)
- Dashboard: [definvestdashboard](https://samuelmoyer91-sketch.github.io/definvestdashboard/)

---

## 📄 License

Created for personal portfolio and professional use.

---

**Last Updated:** January 2026
**Status:** ✅ Live and Auto-Updating
