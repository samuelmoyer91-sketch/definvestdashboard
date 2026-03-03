# Defense Capital Dashboard

A professional dashboard tracking defense sector investments, industrial health, and economic indicators — designed for defense analysts, think tankers, and industry researchers.

**[View Live Dashboard](https://capitalfordefense.com)**

---

## Automated Pipeline

The entire pipeline runs automatically via GitHub Actions — the only manual step is triaging deals.

| Stage | Schedule | How |
|-------|----------|-----|
| **Ingest** (fetch, screen, scrape, AI) | Daily 6 AM ET | GitHub Actions (`ingest.yml`) |
| **Triage** (review/accept/reject deals) | Anytime | Railway web app |
| **Publish** (economic data + deal export + deploy) | Daily 8 PM ET | GitHub Actions (`publish.yml`) |

Both workflows can also be triggered manually: `gh workflow run ingest.yml` or `gh workflow run publish.yml`.

---

## Overview

The dashboard provides visibility into the defense industrial base and capital markets through two lenses:

**Deal Tracker** — Curated private capital investments (VC, PE, M&A, contracts) in defense companies, with AI-assisted triage and human-curated summaries. Includes an investor analytics view with searchable list and per-investor drill-down showing deal history.

**Business Environment Indicators** — 17 indicators on a single page, organized into three sections:
- *Capital Flows* — defense capital goods orders, VC/M&A activity, public company capex & R&D, market sentiment (ITA ETF)
- *Industrial Capacity* — aircraft orders & parts, defense equipment production, federal defense spending, manufacturing construction
- *Macro Environment* — industrial production, business investment, lending standards, ETFs (XLI, PLD), Treasury yields

---

## Architecture

| Component | Purpose | Hosting |
|-----------|---------|---------|
| **Public Dashboard** | Static site with charts and deal feed | Cloudflare Pages (`capitalfordefense.com`) |
| **Triage App** | Web UI for reviewing/curating deals | Railway (24/7) |
| **Database** | Single source of truth for all deal data | Turso (cloud SQLite) |
| **Ingest Pipeline** | RSS fetch, title screening, article scraping, AI extraction | GitHub Actions |
| **Publish Pipeline** | FRED/market data fetch, site generation, Cloudflare deploy | GitHub Actions |

**How it works in practice:**
- New articles flow in automatically every morning
- You triage deals from any device via the Railway app
- Accepted deals and fresh economic data publish automatically every evening
- The public site regenerates the indicators page and deal cards from templates on each publish

---

## Data Sources

| Source | Data | License Status |
|--------|------|----------------|
| **FRED API** | 10+ economic series (defense spending, industrial production, orders, investment, lending) | Public domain, citation requested |
| **Yahoo Finance** | Defense ETFs (ITA), industrials (XLI), REITs (PLD), Treasuries (DGS10) | Displayed with disclaimer, no redistribution |
| **Custom Research** | VC and M&A deal volume, public defense company metrics | Original compilation |
| **RSS/Google Alerts** | Defense sector deal announcements | AI-summarized, human-curated |

This product uses the FRED API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.

---

## Technology Stack

**Frontend:** Chart.js 4.4.0, vanilla JavaScript, responsive CSS, static HTML

**Backend:** Python 3, FRED API client, yfinance, SQLAlchemy, FastAPI (triage UI), Claude AI (Anthropic) for deal extraction and draft summaries

**Infrastructure:** Cloudflare Pages (static site + custom domain), Railway (triage app), Turso (database), GitHub Actions (CI/CD)

**Branding:** B3 "Corner Glow" logo (3x3 grid with opacity gradient), navy (#1e456e) and green (#88c540) palette

---

## Project Structure

```
PC Dashboard/
├── github_site/              # Published website (deployed to Cloudflare Pages)
│   ├── index.html            # Homepage with hero banner
│   ├── charts/               # indicators.html (single page, 17 charts)
│   ├── deals/                # Deal tracker (intelligence briefing style)
│   ├── data/                 # JSON datasets (FRED, finance, custom)
│   ├── css/style.css         # Global styles
│   ├── js/main.js            # Chart utilities
│   └── favicon.svg           # B3 logo favicon
├── src/
│   ├── data_fetchers/        # FRED and Yahoo Finance data fetchers
│   ├── export/               # HTML generators (chart pages, deal feed)
│   ├── scraper/              # RSS fetcher, article scraper, AI summarizer
│   ├── utils/                # AI summarizer (Claude API), investor parser
│   ├── web/                  # Triage app (FastAPI + templates)
│   └── database/             # SQLAlchemy models, Turso connection
├── .github/workflows/
│   ├── ingest.yml            # Daily ingest pipeline
│   └── publish.yml           # Daily publish + deploy pipeline
├── generate_site.py          # Orchestrates data fetch + site generation
├── update_workflow.sh        # Manual workflow helper script
└── requirements.txt          # Python dependencies
```

---

## Deal Curation Pipeline

1. **RSS Fetch** — Google News Alerts deliver defense deal articles
2. **AI Title Screen** — Claude filters noise (earnings calls, opinion pieces) from genuine deals
3. **Article Scraping** — Full article text retrieved for AI processing
4. **AI Extraction** — Claude extracts structured data (company, amount, investors, sectors) and drafts an analytical summary
5. **Human Triage** — Reviewer accepts/rejects deals, edits any field before publication
6. **Investor Normalization** — On accept/edit, investor text is parsed into structured `Investor` records linked to deals. The parser strips AI prose artifacts ("led by", "backed by", "with participation from", semicolons, trailing annotations like "as acquirer") to extract clean entity names. Investor records are deduplicated by slug.
7. **Export** — Only human-approved content appears on the public site (raw AI and RSS data never shown)

Capital type taxonomy: Seed, Venture Capital, Private Equity, Corporate M&A, Government/Contract, Public Markets, Internal/Self-funded, Fund Raise.

---

## Privacy & Security

- Public dashboard is a static site — no user tracking, no cookies
- Triage app is hosted on Railway (not indexed, not publicly linked)
- All data flows through Turso cloud database
- Only human-approved deals appear on the public site
- AI-generated drafts are never published directly

---

## Setup (For Maintenance)

```bash
# Install dependencies
pip3 install -r requirements.txt

# Required environment variables
export FRED_API_KEY='...'
export TURSO_DATABASE_URL='...'
export TURSO_AUTH_TOKEN='...'
export ANTHROPIC_API_KEY='...'

# Run locally
cd github_site && python3 -m http.server 8080

# Generate site (fetches fresh data + rebuilds all pages)
python3 generate_site.py

# Deploy manually
gh workflow run publish.yml
```

---

## Contact

**Sam Moyer**
- GitHub: [@samuelmoyer91-sketch](https://github.com/samuelmoyer91-sketch)
- Dashboard: [capitalfordefense.com](https://capitalfordefense.com)

---

**Status:** Live — fully automated via GitHub Actions
