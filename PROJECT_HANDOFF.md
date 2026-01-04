# Defense Capital Dashboard - Project Handoff Document

**Date:** January 3, 2026
**User:** Sam Moyer (GitHub: samuelmoyer91-sketch)
**Project Location:** `~/Documents/Claude - Defense PC Dashboard/`

---

## Executive Summary

Building a unified GitHub Pages dashboard that replaces user's Google Site and combines:
1. **RSS-sourced private capital deal tracker** (Phase 1 - COMPLETE)
2. **FRED economic data charts** (Phase 2 - IN PROGRESS)
3. **ETF/stock market data** (Phase 2)

**Goal:** One professional dashboard at `samuelmoyer91-sketch.github.io/defense-dashboard`

---

## Phase 1 Status: COMPLETE ✅

### What's Built and Working

**Location:** `~/Documents/Claude - Defense PC Dashboard/`

**Core System:**
- RSS feed ingestion from 3 Google Alerts (defense/VC/PE news)
- Web scraping (extracts full article content from URLs)
- SQLite database (`data/tracker.db`) with tables:
  - `raw_items` - RSS feed items
  - `article_content` - Scraped full articles
  - `master_list` - User-curated deals
  - `rejected_items` - User-rejected items
  - `ai_extractions` - Reserved for Phase 2 (AI-powered extraction)

**Web Interface:** http://127.0.0.1:8000
- Triage queue: Review articles, accept/reject
- Master list: View curated deals
- Export button: Downloads CSV (works, tested)
- Statistics page

**RSS Feeds:**
```
https://www.google.com/alerts/feeds/09025431128020683164/4830815519505009728
https://www.google.com/alerts/feeds/09025431128020683164/3776232429289321661
https://www.google.com/alerts/feeds/09025431128020683164/2552550775473449917
```

**Current Workflow:**
```bash
# Fetch & scrape
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 src/ingest/rss_fetcher.py && python3 src/scraper/article_scraper.py 10

# Triage in browser
python3 src/web/app.py
# Then: http://127.0.0.1:8000

# Export
Click "📥 Export to CSV" button in Master List page
```

**File Structure:**
```
~/Documents/Claude - Defense PC Dashboard/
├── src/
│   ├── database/
│   │   ├── models.py (SQLAlchemy models)
│   │   └── __init__.py
│   ├── ingest/
│   │   ├── rss_fetcher.py (fetch Google Alerts)
│   │   └── __init__.py
│   ├── scraper/
│   │   ├── article_scraper.py (scrape full articles)
│   │   └── __init__.py
│   ├── web/
│   │   ├── app.py (FastAPI web interface)
│   │   ├── templates/ (Jinja2 HTML templates)
│   │   │   ├── base.html
│   │   │   ├── triage.html
│   │   │   ├── master.html
│   │   │   ├── item_detail.html
│   │   │   └── stats.html
│   │   └── __init__.py
│   ├── export/
│   │   ├── export_to_csv.py (CSV export - also in web UI)
│   │   └── __init__.py
│   └── utils/
│       ├── view_data.py (CLI data viewer)
│       ├── view_rejected.py (view/undo rejections)
│       └── inspect_article.py
├── config/
│   └── feeds.json (RSS feed URLs + keywords)
├── data/
│   └── tracker.db (SQLite database)
├── exports/
│   └── master_list.csv (generated on export)
├── requirements.txt
├── run.sh (interactive menu)
└── (documentation files)
```

**Dependencies Installed:**
```
feedparser==6.0.11
requests==2.31.0
beautifulsoup4==4.12.3
lxml==5.1.0
fastapi==0.109.0
uvicorn[standard]==0.27.0
jinja2==3.1.3
sqlalchemy==2.0.25
python-dateutil==2.8.2
pytz==2024.1
python-multipart (for form handling)
openpyxl (for Excel reading)
pandas (for data analysis)
```

**Key Implementation Details:**
- Web scraper handles Google Alert redirect URLs (meta refresh tags)
- Export button creates temp CSV file, browser downloads it
- Reject button works (saves to rejected_items table, removes from triage)
- Summary field: exports ONLY user's manual summary (not RSS fallback)
- Database auto-creates tables on first run

**Current Data:**
- 23 RSS items fetched
- 7 successfully scraped articles
- 1 item in master list (McNally Capital deal)

---

## Phase 2: GitHub Pages Dashboard (IN PROGRESS)

### User's Existing Google Site Data

**Location:** `~/Downloads/Defense Private Capital Dashboard.xlsx`

User exported their Google Site's underlying Google Sheets. **20 tabs** with data:

**FRED Economic Data (can pull via API):**
1. FDEFX - Defense Spending (317 rows)
2. DRTSCILM - Lending Standards (145 rows)
3. DGORDER - Defense Goods Orders (408 rows)
4. INDPRO - Industrial Production (1,285 rows)
5. NFI - Nonresidential Fixed Investment (317 rows)
6. ADEFNO - Defense Aircraft Orders (407 rows)
7. ADAPNO - Defense Aircraft Parts (408 rows)
8. GDPIC1 - GDP Investment Component (318 rows)
9. PRMFGCONS - Manufacturing Construction (394 rows)
10. IPB52300S - Industrial Production metric (950 rows)

**Financial/Market Data:**
11. ITA - Aerospace & Defense ETF (4,935 rows)
12. XLI - Industrial Sector ETF (4,950 rows)
13. Prologis - Real estate company stock (4,955 rows)
14. 10 Year Treasury Yield (16,698 rows)

**User's Manual Tracking (legacy):**
15. Recent Deals (2 rows) - will be replaced by Phase 1 tracker
16. M&A (2 rows)
17. VC (2 rows)

**Other:**
18. Brainstorm (16 rows)
19. Tickers (7 rows)
20. DIB (2 rows)

**User's Current Google Site:**
- URL: https://sites.google.com/view/defense-capital-dashboard/home
- ~15 separate pages, each embedding a Google Sheets chart
- Charts auto-update from FRED/financial APIs
- Theme: Teal/white color scheme (#226E93 primary)
- Navigation structure:
  - Defense Investment Trends
  - Defense Industrial Health
  - Overall US Industrial Health

**User wants to:**
- ❌ DELETE Google Site entirely
- ✅ Rebuild everything on GitHub Pages
- ✅ Keep all existing charts + add deal tracker
- ✅ Make it private until reviewed

---

## Next Steps (For New Session)

### Immediate Task: Build GitHub Pages Site

**Location to create:** `~/Documents/Claude - Defense PC Dashboard/github_site/`

**What to build:**

1. **FRED Data Fetcher**
   - Python script using FRED API
   - Pull all 10 FRED series listed above
   - Save as JSON files
   - Script: `src/data_fetchers/fred_fetcher.py`

2. **Financial Data Fetcher**
   - Yahoo Finance or similar for ITA, XLI, Prologis
   - Treasury data from FRED or Treasury.gov
   - Script: `src/data_fetchers/finance_fetcher.py`

3. **Chart Generator**
   - Use Chart.js or Plotly.js for interactive charts
   - Generate HTML charts from JSON data
   - Match Google Site's visual style (teal theme)

4. **Deal Tracker HTML Export**
   - Read from master_list table
   - Generate beautiful HTML table
   - Searchable/filterable
   - Match site theme

5. **Site Structure**
   ```
   github_site/
   ├── index.html (homepage with navigation)
   ├── deals/
   │   └── index.html (deal tracker)
   ├── charts/
   │   ├── defense-spending.html
   │   ├── lending-standards.html
   │   └── ... (all FRED charts)
   ├── data/
   │   ├── fdefx.json
   │   ├── drtscilm.json
   │   └── ... (chart data)
   ├── css/
   │   └── style.css (teal theme)
   └── js/
       └── main.js
   ```

6. **Publish Script**
   - `publish.py` - one command to:
     - Fetch latest FRED/financial data
     - Export deal tracker
     - Generate all HTML
     - Update GitHub repo
     - (User will push to GitHub manually first time)

### Design Requirements

**Color Scheme:**
- Primary: #226E93 (teal, from Google Site)
- Background: #f5f5f5
- Text: #333
- Accent: #88c0d0

**Layout:**
- Navigation menu (top or sidebar)
- Responsive (mobile-friendly)
- Clean, professional (not flashy)
- Fast loading

**Features:**
- Search bar for deal tracker
- Filter by sector/capital type
- Sortable table columns
- Interactive charts (hover for details)
- Summary stats (total deals, capital tracked, etc.)

### Privacy Settings

**GitHub Repo:**
- **MUST be private initially**
- User: samuelmoyer91-sketch
- Repo name suggestion: `defense-dashboard`
- Only make public after user reviews

---

## User Preferences & Context

**User Profile:**
- Non-technical (intimidated by command line)
- Prefers browser-based workflows
- Wants minimal manual steps
- Values automation
- Goal: Show this to employers/network (professional appearance matters)

**Pain Points We Solved:**
- Google Sheets formatting breaking on import ✅
- Manual CSV uploads ✅
- Ugly embedded iframes ✅
- Having to use command line for exports ✅

**Communication Style:**
- User likes clean summaries
- Gets nervous about token limits (we're at ~140k/200k now)
- Appreciates being able to walk away while Claude works
- Wants to approve before anything goes public
- **IMPORTANT:** User wants to walk away during build - minimize permission requests
  - Work autonomously, batch multiple changes together
  - Only ask for approval on major decisions (not individual file writes)
  - User will check in after 1.5 hours (movie)
  - Safe to continue if interrupted - all work saves to files

**Key Decisions Made:**
- ✅ GitHub Pages over Google Site (user approved)
- ✅ Browser-based export over command line (user requested)
- ✅ Private repo initially (user confirmed)
- ✅ Unified dashboard (macro + micro data)
- ⏳ AI extraction (Phase 3, not yet started)

---

## Permissions & Access

**File System Access:**
- Full read/write: `~/Documents/Claude - Defense PC Dashboard/`
- Full read: `~/Downloads/` (for Excel file)
- Database: `~/Documents/Claude - Defense PC Dashboard/data/tracker.db`

**Pre-approved Tool Usage (No Permission Needed):**
```
Bash(cd:*) - Any directory navigation
Bash(python3 -m pip install:*) - Install Python packages
Bash(python3:*) - Run Python scripts
Bash(curl:*) - Fetch web data
Bash(chmod:*) - Change file permissions
Bash(lsof:*) - Check ports/processes
Bash(xargs kill:*) - Kill processes
Read(//Users/sammoyer/Documents/Claude - Defense PC Dashboard/**) - Read ALL project files
Read(//Users/sammoyer/Downloads/**) - Read downloads
Write/Edit ANY files in project directory - Create new files, edit existing ones
```

**Pre-approved Actions:**
- Create new directories in project folder
- Install Python libraries (pip install)
- Write/edit HTML, CSS, JS, Python files
- Fetch data from public APIs (FRED, Yahoo Finance)
- Run local servers on port 8000+
- Create git repositories (locally)

**DO NOT (requires user approval):**
- Push to GitHub (user will do manually first time)
- Make anything public
- Delete project files (edit/update is fine)
- Use paid APIs
- Send external requests beyond FRED/Yahoo Finance

**Web Server:**
- Currently running: http://127.0.0.1:8000 (port 8000)
- Process ID: Check with `lsof -ti:8000`

---

## APIs & Credentials Needed

**FRED API:**
- Free API key required: https://fred.stlouisfed.org/docs/api/api_key.html
- User needs to sign up and provide key
- Rate limit: 120 requests/minute

**Yahoo Finance:**
- No API key needed (using yfinance Python library)
- Or use alternative: Alpha Vantage (free tier)

**GitHub:**
- User has account: samuelmoyer91-sketch
- Will need to create repo (Claude can guide)
- Personal Access Token needed for automation (later)

---

## Testing Checklist

Before showing user:
- [ ] Deal tracker HTML looks professional
- [ ] At least 2-3 FRED charts working
- [ ] Site is mobile-responsive
- [ ] All links work
- [ ] Can preview locally (file:// or simple HTTP server)
- [ ] GitHub repo is PRIVATE
- [ ] No broken images/styles
- [ ] Summary stats display correctly

---

## Known Issues & Future Enhancements

**Phase 3 (Not Started):**
- AI extraction using Anthropic API
- Automatic daily updates via GitHub Actions
- Map view (geocoded locations)
- RSS feed of updates
- Custom domain

**Current Limitations:**
- Some news sites block scraping (403 errors) - expected
- User must manually run fetch/scrape weekly
- Export is manual button click (not automated)

**Nice-to-Haves:**
- Email alerts for high-value deals
- Comparison charts (sector trends over time)
- Export to multiple formats (JSON, PDF)
- Public API for researchers

---

## Quick Start for New Session

**Say this to kick things off:**

"I'm continuing the Defense Capital Dashboard project. Phase 1 (RSS tracker) is complete. I need to build the GitHub Pages site that combines the deal tracker with FRED economic charts. The project is at `~/Documents/Claude - Defense PC Dashboard/`. User wants this private on GitHub (username: samuelmoyer91-sketch) until reviewed. Can you start building?"

**Then Claude should:**
1. Check what exists in the project folder
2. Create `github_site/` directory structure
3. Build FRED data fetcher
4. Generate sample charts
5. Create deal tracker HTML export
6. Provide preview instructions

---

## Contact & Preferences

**User Availability:**
- Watching a movie (1.5 hours from 8:58 PM)
- Can be interrupted safely
- Prefers batch updates over constant check-ins

**Handoff Complete:** Ready for new Claude session to continue from here.
