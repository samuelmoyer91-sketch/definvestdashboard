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
- **⬇️ CSV Export** - One-click download of full datasets for custom analysis
- **🔍 Key Insights** - Curated context explaining metric relationships
- **📅 Timestamps** - Data freshness displayed on every page
- **📱 Mobile Responsive** - Professional design on all devices
- **🤖 AI Deal Summaries** - Claude-powered analysis of defense investments (optional)

### Interactive Charts:
- Hover for exact values
- Clean, focused visualizations
- Last 10 years displayed by default
- Full historical data available

### Intelligence Briefing Deal Feed:
- Professional briefing-style layout for government analysts
- AI-extracted deal information (company, amount, investors, significance)
- Real-time search and filtering by deal type
- Chronological feed with pagination
- Graceful fallback to RSS summaries

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

### Quick Data Update
```bash
# 1. Update all data and regenerate site
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 publish.py

# 2. Deploy to live site
git add -A
git commit -m "Weekly update - $(date +%Y-%m-%d)"
git push origin main

# Site updates in ~30 seconds!
```

**Time required:** 5 minutes

### With AI Deal Summaries

For the deal tracker, you can generate AI-powered summaries:

```bash
# 1. Fetch new articles from RSS
python3 src/scraper/rss_fetcher.py

# 2. Scrape article content
python3 src/scraper/article_scraper.py

# 3. Generate AI summaries (requires ANTHROPIC_API_KEY)
python3 src/scraper/generate_ai_summaries.py --limit 10

# 4. Review and curate deals
cd src/export
python3 -m http.server 8080
# Open http://localhost:8080/deals_triage.html

# 5. Publish with updated deals
python3 publish.py
git add -A
git commit -m "Update deals with AI summaries"
git push
```

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
├── docs/
│   └── AI_WORKFLOW.md       # AI summary setup and usage guide
├── publish.py               # Unified update script
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

### Update Data:
```bash
python3 publish.py
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
