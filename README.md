# Defense Private Capital Intelligence Platform

A platform for tracking and analyzing private capital investments in U.S. defense and dual-use infrastructure.

## Overview

This system:
1. Ingests RSS feeds from Google Alerts
2. Scrapes full article content
3. (Future) AI-extracts structured data (company, investment amount, sector, etc.)
4. Provides a triage interface for human curation
5. (Future) Publishes a public-facing dashboard

## Project Structure

```
.
├── src/
│   ├── ingest/          # RSS feed ingestion
│   ├── scraper/         # Web scraping
│   ├── extractor/       # AI data extraction (v2)
│   ├── database/        # Database models and operations
│   └── web/             # Web UI (triage and dashboard)
├── config/              # Configuration files
├── data/                # SQLite database
├── logs/                # Application logs
├── requirements.txt     # Python dependencies
└── README.md
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure RSS feeds in `config/feeds.json`

3. Run the ingestion:
   ```bash
   python -m src.ingest.rss_fetcher
   ```

4. Start the triage web UI:
   ```bash
   python -m src.web.app
   ```

## Development Phases

### Phase 1 (Current)
- [x] RSS ingestion
- [x] Basic web scraping
- [x] SQLite setup
- [ ] Simple triage UI

### Phase 2 (Future)
- [ ] Claude API integration for data extraction
- [ ] Enhanced triage UI with AI extractions
- [ ] Human verification workflow

### Phase 3 (Future)
- [ ] Public dashboard
- [ ] Search/filter capabilities
- [ ] Map view (if locations available)

## RSS Feeds

Currently monitoring:
- Google Alert Feed 1: Defense manufacturing
- Google Alert Feed 2: Private equity defense
- Google Alert Feed 3: Dual-use technology investments
