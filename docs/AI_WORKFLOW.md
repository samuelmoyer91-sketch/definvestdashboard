# AI Summary Workflow

This document explains how to use the AI-powered intelligence briefing feature for the Defense Capital Dashboard.

## Overview

The dashboard now includes AI-powered summaries for defense investment deals using Claude (Anthropic). The AI analyzes scraped articles and extracts:

- **Company name** and description
- **Deal type** (VC, M&A, IPO, etc.)
- **Deal amount** and investors
- **Strategic significance** (why it matters)
- **Market implications** (what it signals)

## Prerequisites

### 1. Set up Anthropic API Key

You'll need an API key from Anthropic to use Claude for AI summaries.

**Get your API key:**
1. Visit: https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key

**Set the API key permanently:**

Add to your shell profile (~/.zshrc or ~/.bashrc):

```bash
echo "export ANTHROPIC_API_KEY='your_key_here'" >> ~/.zshrc
source ~/.zshrc
```

**Verify it's set:**

```bash
echo $ANTHROPIC_API_KEY
```

### 2. Install Dependencies

Make sure the Anthropic SDK is installed:

```bash
pip install anthropic>=0.40.0
```

## Workflow

### Step 1: Fetch RSS Feeds

Collect new defense investment articles from RSS feeds:

```bash
python3 src/scraper/rss_fetcher.py
```

This populates the `raw_items` table with articles.

### Step 2: Scrape Article Content

Download and extract the full text of articles:

```bash
python3 src/scraper/article_scraper.py
```

This populates the `article_content` table with clean text.

### Step 3: Generate AI Summaries

Analyze articles with Claude to extract structured deal information:

```bash
python3 src/scraper/generate_ai_summaries.py
```

**Options:**
- `--limit N` - Process only N articles (default: 5)
- `--force` - Regenerate summaries even if they exist

**Example:**
```bash
# Process 10 articles
python3 src/scraper/generate_ai_summaries.py --limit 10

# Regenerate all summaries
python3 src/scraper/generate_ai_summaries.py --force
```

**What it does:**
- Finds articles without AI summaries
- Sends article content to Claude API
- Extracts structured data using JSON schema
- Stores results in `ai_extractions` table
- Marks extraction as complete

**Rate limiting:**
- Includes 1-second delay between API calls
- Respects Anthropic's rate limits
- Safely handles API errors

### Step 4: Curate Deals (Triage UI)

Review AI-extracted deals and approve for publication:

```bash
cd src/export
python3 -m http.server 8080
```

Open: http://localhost:8080/deals_triage.html

**In the triage UI:**
1. Review AI-extracted information
2. Edit any fields if needed
3. Click "Publish to Master List"
4. Deals appear on the public dashboard

### Step 5: Publish to GitHub Pages

Generate the intelligence briefing and all chart pages:

```bash
python3 publish.py
```

Then push to GitHub:

```bash
cd github_site
git add .
git commit -m "Update deal feed and charts"
git push
```

## Database Schema

### ai_extractions Table

Stores AI-extracted deal information:

| Column | Type | Description |
|--------|------|-------------|
| `company` | String | Company name |
| `company_description` | Text | What the company does (1 sentence) |
| `deal_type` | String | VC, M&A, IPO, etc. |
| `deal_amount` | String | Investment amount (e.g., "$300M") |
| `investors` | Text | Key investors/acquirers |
| `strategic_significance` | Text | Why this matters (2-3 sentences) |
| `market_implications` | Text | What this signals (1-2 sentences) |
| `summary_complete` | Boolean | Was extraction successful? |
| `model_used` | String | Claude model used |
| `extracted_at` | DateTime | When extracted |

## Files Reference

### Core AI Modules

- **`src/utils/ai_summarizer.py`** - Claude API integration for extracting deal information
- **`src/scraper/generate_ai_summaries.py`** - Batch processing script for AI summaries
- **`src/database/models.py`** - Database schema including AIExtraction model

### Export Scripts

- **`src/export/export_to_html_v2.py`** - Generates intelligence briefing HTML
- **`src/export/deals_triage.html`** - Web UI for curating deals

### Database Migrations

- **`src/database/migrate_ai_fields.py`** - Adds AI summary columns to database

## Intelligence Briefing Features

The generated deal feed (`github_site/deals/index.html`) includes:

- **Professional Layout**: Intelligence briefing style, analyst-friendly
- **Deal Cards**: Clean, scannable cards with AI summaries
- **Search**: Real-time filtering by keywords
- **Deal Type Filters**: Filter by VC, M&A, IPO, etc.
- **Badges**: Color-coded deal type indicators
- **Graceful Fallback**: Shows RSS summary if AI summary unavailable
- **Mobile Responsive**: Works on all devices

## Cost Management

### API Costs

- Claude Sonnet 4: ~$3 per million input tokens, ~$15 per million output tokens
- Average article: ~3,000 tokens input, ~500 tokens output
- Cost per article: ~$0.01 - $0.02

**Budget-friendly practices:**
1. Use `--limit` flag to process small batches
2. Review articles in triage before generating summaries
3. Don't use `--force` unless necessary (avoids re-generating)

### Example Monthly Cost

Processing 100 articles/month:
- Input: 100 × 3,000 tokens = 300,000 tokens = $0.90
- Output: 100 × 500 tokens = 50,000 tokens = $0.75
- **Total: ~$1.65/month**

## Troubleshooting

### API Key Not Found

**Error:** `Error: ANTHROPIC_API_KEY environment variable not set`

**Solution:**
```bash
export ANTHROPIC_API_KEY='your_key_here'
# Or add to ~/.zshrc for persistence
```

### No Articles to Process

**Message:** `No articles found without AI summaries`

**Solutions:**
1. Run `python3 src/scraper/rss_fetcher.py` to get new articles
2. Run `python3 src/scraper/article_scraper.py` to scrape content
3. Use `--force` flag to regenerate existing summaries

### Database Column Errors

**Error:** `no such column: ai_extractions.deal_type`

**Solution:**
```bash
python3 src/database/migrate_ai_fields.py
```

### API Rate Limits

**Error:** `Rate limit exceeded`

**Solution:**
- Wait a few minutes and retry
- Use smaller `--limit` values
- Script includes automatic 1-second delays

## Best Practices

1. **Regular Updates**: Run AI summaries weekly or bi-weekly
2. **Small Batches**: Process 5-10 articles at a time
3. **Review in Triage**: Always review AI extractions before publishing
4. **Version Control**: Commit database after AI summaries
5. **Backup**: Keep backups of `data/tracker.db` before major updates

## Future Enhancements

Potential improvements to the AI workflow:

- **🔄 Workflow Optimization (High Priority)**: Change workflow to "Curate First, AI Second" - only generate AI summaries for articles that have been approved in triage. This would save API costs by not analyzing articles that might be rejected. Current workflow: RSS → Scrape → AI → Triage → Publish. Proposed: RSS → Scrape → Triage → AI (only approved) → Publish.
- **Batch API calls**: Process multiple articles in parallel
- **Confidence scoring**: Flag low-confidence extractions for review
- **Custom prompts**: Tailor extraction for specific deal types
- **Auto-publishing**: Skip triage for high-confidence extractions
- **Email alerts**: Notify on high-priority deals
- **Trend detection**: AI analysis of market patterns

## Questions?

For questions or issues with the AI workflow, check:
- Anthropic API docs: https://docs.anthropic.com/
- Claude model info: https://www.anthropic.com/claude
- Project README: ../README.md
