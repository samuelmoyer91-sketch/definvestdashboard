# Defense Capital Tracker - System Architecture

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GOOGLE ALERTS (RSS)                          │
│  • Defense Manufacturing                                             │
│  • Private Equity Defense                                            │
│  • Dual-Use Tech Investments                                         │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │   RSS INGESTION MODULE         │
        │   (src/ingest/rss_fetcher.py)  │
        │   • Pulls feeds                │
        │   • Deduplicates by URL        │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────────┐
        │   RAW_ITEMS TABLE                   │
        │   • URL, title, summary             │
        │   • Published date                  │
        │   • Feed source                     │
        └────────────┬────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────┐
        │   WEB SCRAPER MODULE               │
        │   (src/scraper/article_scraper.py) │
        │   • Follows redirects              │
        │   • Extracts full text             │
        │   • Handles paywalls gracefully    │
        └────────────┬───────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────┐
        │   ARTICLE_CONTENT TABLE              │
        │   • Full HTML                        │
        │   • Clean text                       │
        │   • Scrape status                    │
        └────────────┬───────────────────────┬─┘
                     │                       │
                     │                       │ (Future: Phase 2)
                     │                       │
                     │                       ▼
                     │          ┌─────────────────────────────┐
                     │          │   AI EXTRACTION MODULE      │
                     │          │   (Claude API)              │
                     │          │   • Extract company         │
                     │          │   • Extract investment $    │
                     │          │   • Extract location        │
                     │          │   • Generate summary        │
                     │          └─────────────┬───────────────┘
                     │                        │
                     │                        ▼
                     │          ┌─────────────────────────────┐
                     │          │   AI_EXTRACTIONS TABLE      │
                     │          │   • Structured data         │
                     │          │   • Confidence scores       │
                     │          └─────────────┬───────────────┘
                     │                        │
                     ▼                        ▼
        ┌─────────────────────────────────────────────────┐
        │         TRIAGE WEB INTERFACE                    │
        │         (http://127.0.0.1:8000)                 │
        │   • Review articles                             │
        │   • Manual data entry (or edit AI extractions)  │
        │   • Accept/Reject decisions                     │
        └────────────┬────────────────────────────────────┘
                     │
                     ▼ (Accept)
        ┌──────────────────────────────────────┐
        │   MASTER_LIST TABLE                  │
        │   • Human-verified data              │
        │   • Publication-ready                │
        │   • Company, investment, location    │
        │   • Sector, project type, summary    │
        └────────────┬───────────────────────┬─┘
                     │                       │
                     ▼                       ▼ (Future: Phase 3)
        ┌─────────────────────┐   ┌──────────────────────────┐
        │   MASTER LIST VIEW  │   │   PUBLIC DASHBOARD       │
        │   (Internal)        │   │   • Static site export   │
        └─────────────────────┘   │   • Search/filter UI     │
                                  │   • Map view             │
                                  │   • Export CSV/JSON      │
                                  └──────────────────────────┘
```

## Database Schema

### raw_items
- Stores every RSS feed item
- Deduplicates by URL
- Tracks scrape status

### article_content
- Full scraped article HTML and text
- Links to raw_items via item_id
- Tracks success/failure

### ai_extractions (Phase 2)
- AI-extracted structured data
- Links to raw_items via item_id
- Stores confidence scores

### master_list
- Human-curated final dataset
- Can override AI extractions
- Publication-ready

## Technology Stack

**Backend:**
- Python 3.11+
- FastAPI (web framework)
- SQLAlchemy (database ORM)
- SQLite (database)

**RSS & Scraping:**
- feedparser (RSS parsing)
- requests + BeautifulSoup (web scraping)

**Frontend:**
- Jinja2 templates
- HTML/CSS (minimal, clean design)

**Future (Phase 2):**
- Anthropic Python SDK (AI extraction)

## Key Design Decisions

### Why SQLite?
- **Simple:** No database server required
- **Portable:** Single file, easy to backup
- **Sufficient:** Handles thousands of records easily
- **Local:** Full data ownership

### Why Local Web Scraping?
- **Control:** No API quotas or costs
- **Flexibility:** Can adjust scraping logic
- **Privacy:** All data stays local
- **Debugging:** Easy to inspect and fix

### Why Manual Triage (Phase 1)?
- **Accuracy:** Human verification ensures quality
- **Learning:** Understand your data before automating
- **Flexibility:** Can add context and notes
- **Cost:** Free (vs AI extraction costs)

### When to Add AI (Phase 2)?
- After you've triaged 20-50 items manually
- When you understand common patterns
- When data entry becomes tedious
- Cost: ~$0.01-0.05 per article

## Operational Workflow

### Daily/Weekly Routine
1. **Ingest:** Pull new RSS items
2. **Scrape:** Extract full articles
3. **Triage:** Review and curate via web UI
4. **Publish:** Export master list

### Time Investment
- **Initial setup:** Done!
- **Weekly maintenance:** 15-30 minutes
- **With AI (Phase 2):** 5-10 minutes

## Extensibility

### Easy to Add
- New RSS feeds (edit `config/feeds.json`)
- New extraction fields (add columns to master_list)
- Export formats (CSV, JSON, etc.)
- Filtering/search (web UI)

### Phase 2 Features
- AI extraction with Claude
- Bulk operations
- Scheduled automation (cron)

### Phase 3 Features
- Public-facing dashboard
- Map view (geocoded locations)
- API for external access
- Email alerts for high-priority items

## Why This Architecture?

✅ **Debuggable:** Every step is visible and inspectable
✅ **Iterative:** Can improve piece by piece
✅ **Cost-effective:** Mostly free, AI optional
✅ **Sustainable:** Runs locally, no vendor lock-in
✅ **Scalable:** Can handle 10,000+ items
✅ **Professional:** Clean code, proper database
