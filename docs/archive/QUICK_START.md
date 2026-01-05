# Defense Capital Tracker - Quick Start Guide

## What You Built

A complete intelligence platform for tracking private capital investments in U.S. defense and dual-use infrastructure!

### Key Features
- ✅ Automated RSS feed ingestion from Google Alerts
- ✅ Web scraping with full article content extraction
- ✅ SQLite database for organized data storage
- ✅ Web-based triage interface for manual curation
- ✅ Master list for publication-ready items
- 🔄 AI-powered extraction (coming in v2)

## Current Status

You have **23 items** from your RSS feeds, and **7 successfully scraped** articles ready for triage.

## How to Use

### Option 1: Interactive Menu (Recommended)

```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
./run.sh
```

This launches an interactive menu with all operations.

### Option 2: Individual Commands

#### 1. Fetch New RSS Items
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 src/ingest/rss_fetcher.py
```

Run this daily/weekly to pull new items from your Google Alerts.

#### 2. Scrape Full Articles
```bash
# Scrape 10 articles at a time (recommended)
python3 src/scraper/article_scraper.py 10

# Or scrape all pending
python3 src/scraper/article_scraper.py
```

This fetches full article content from the URLs found in RSS feeds.

**Note:** Some sites (like NY Times) block scraping with 403 errors - that's expected.

#### 3. Start the Web Interface
```bash
python3 src/web/app.py
```

Then open your browser to: **http://127.0.0.1:8000**

You'll see:
- **Triage Queue** - Review scraped articles
- **Master List** - Your curated database
- **Statistics** - Overview of your data

#### 4. Triage Workflow

1. Go to **http://127.0.0.1:8000** (Triage Queue)
2. Click **"Review & Accept"** on an item
3. Fill in the extraction fields:
   - Company (e.g., "Anduril, Shield AI")
   - Investment Amount (e.g., "$100M")
   - Capital Type (VC, PE, Corporate, etc.)
   - Location
   - Sector (Drones, Semiconductors, etc.)
   - Project Type (Factory, Acquisition, etc.)
   - Summary (2-3 sentences)
4. Click **"Accept & Add to Master List"**
5. Your curated item now appears in the Master List!

#### 5. View Your Master List

Go to **http://127.0.0.1:8000/master**

This is your publication-ready dataset. Eventually, this will be your public dashboard.

## Your Workflow (Weekly)

```bash
# 1. Pull new items
./run.sh  # Choose option 1

# 2. Scrape articles
./run.sh  # Choose option 3 (10 at a time)

# 3. Open web interface
./run.sh  # Choose option 4

# 4. Triage in your browser at http://127.0.0.1:8000

# 5. Export to CSV for Google Sheets
./run.sh  # Choose option 5

# 6. Upload CSV to Google Sheets (see GOOGLE_SITES_SETUP.md)
```

## Example: What a Curated Item Looks Like

Here's a real item from your feed:

**McNally Capital Acquires PT6A MRO Specialist ATS**
- **Company:** McNally Capital
- **Investment Type:** Private Equity Acquisition
- **Sector:** Aerospace MRO
- **Summary:** McNally Capital, a mid-market aerospace and defense PE firm, acquired ATS, a specialist in PT6A engine maintenance, repair, and overhaul services.
- **Source:** [Link to article]

## What's Next (Phase 2)

When you're ready, we can add:

### AI-Powered Extraction
Get an Anthropic API key (takes 2 minutes at console.anthropic.com) and I'll add:
- Automatic extraction of company, investment amount, location, etc.
- AI-generated summaries
- Confidence scores

This will save you 80% of manual data entry!

### Public Dashboard
- Export your master list as a searchable public website
- Optional map view (if locations are tagged)
- Filtering by sector, capital type, etc.

## Troubleshooting

**Server won't start?**
```bash
# Check if port 8000 is already in use
lsof -ti:8000

# If it is, kill the process:
kill -9 $(lsof -ti:8000)
```

**No items in triage queue?**
1. First, fetch RSS feeds: `python3 src/ingest/rss_fetcher.py`
2. Then scrape: `python3 src/scraper/article_scraper.py 10`
3. Refresh the web interface

**403 errors when scraping?**
Some news sites block automated scraping. That's expected - just skip those items.

## File Structure

```
.
├── src/
│   ├── ingest/          # RSS fetching
│   ├── scraper/         # Web scraping
│   ├── database/        # SQLite models
│   ├── web/             # Triage web app
│   └── utils/           # Helper scripts
├── config/
│   └── feeds.json       # Your RSS feed URLs
├── data/
│   └── tracker.db       # SQLite database
├── run.sh               # Quick start menu
└── README.md
```

## Your Data

Everything is stored in: `data/tracker.db`

This is a SQLite database - portable, easy to backup, and no server needed!

## Questions?

The system is fully operational and ready to use. When you're ready for Phase 2 (AI extraction), just let me know!

Happy tracking! 🚀
