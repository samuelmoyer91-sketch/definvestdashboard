# AI Summary Workflow

This document explains how to use the AI-powered intelligence briefing feature for the Defense Capital Dashboard.

## Overview

The dashboard includes AI-assisted deal curation using Claude (Anthropic). The AI analyzes scraped articles and **drafts suggestions** for:

- **Company name** and description
- **Transaction type** (Equity Funding Round, Acquisition, Merger, Contract/Award, etc.)
- **Capital sources** (multi-select: Venture Capital, Corporate Venture, Private Equity, Government/Contract, etc.)
- **Sectors** (multi-select: AI/ML, Autonomous Systems/Drones, Space/Satellites, Aerospace, Cybersecurity, etc.)
- **Deal amount** and investors
- **Summary** combining strategic significance and market implications

**Critical distinction:** AI suggestions are drafts that pre-populate the triage form. You review and edit everything. The published dashboard shows only what you approve - never raw AI output.

## Data Flow

```
RSS Feed → Scrape Article → AI Drafts Suggestions → YOU REVIEW/EDIT → Publish to Dashboard
                                                            ↓
                                                    (What you type here
                                                     is what publishes)
```

**AI Role:** Drafting assistant that saves you time
**Your Role:** Editor and final authority on all published content
**Published Output:** 100% human-curated (your edits from triage)

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

Review AI-extracted deals and approve for publication using the FastAPI triage interface:

```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
uvicorn src.web.app:app --reload
```

Open: http://127.0.0.1:8000

**In the triage UI:**
1. See collapsed cards with AI one-liners (Transaction Type • Amount • Sector)
2. Click "▼ Review & Accept" to expand inline
3. Review AI-populated fields (blue backgrounds indicate AI data)
4. **Edit the category fields:**
   - **Transaction Type**: Single-select dropdown (Equity Funding Round, Acquisition, Merger, etc.)
   - **Capital Sources**: Multi-select checkboxes (Venture Capital, Corporate Venture, Private Equity, etc.)
   - **Sectors**: Multi-select checkboxes (AI/ML, Autonomous Systems/Drones, Space/Satellites, etc.)
5. **Edit the summary section** - AI pre-drafts a summary combining strategic significance and market implications (you can write your own or edit the AI draft)
6. Edit company name, investors, amounts, or any other field as needed
7. Expand article preview to validate information
8. Click "✓ Accept & Add to Master List" to publish
9. Or click "Reject" for irrelevant articles

**IMPORTANT:** Whatever you type in the triage form is exactly what appears on the published dashboard. AI suggestions are drafts only - they never bypass your review.

**Features:**
- Collapsible inline expansion (no page navigation)
- AI pre-populated fields with visual indicators
- **Enhanced category system** with multi-select checkboxes for Capital Sources and Sectors
- **Human-curated summaries** - what you review is what gets published
- Full article preview for validation
- **Backward compatibility**: Old deals with legacy fields still display correctly

### Step 5: Publish to GitHub Pages

**Recommended: Use the automated workflow script**

```bash
./update_workflow.sh publish
```

This automatically:
- Refreshes FRED economic data
- Refreshes Yahoo Finance market data
- Generates all chart pages
- Exports accepted deals to intelligence briefing format
- Commits changes
- Deploys to GitHub Pages

**Manual alternative (advanced):**

```bash
python3 generate_site.py
cd github_site
git add .
git commit -m "Update deal feed and charts"
git push
git subtree push --prefix github_site origin gh-pages
```

## Database Schema

### ai_extractions Table

Stores AI-extracted deal information:

| Column | Type | Description |
|--------|------|-------------|
| `company` | String | Company name |
| `company_description` | Text | What the company does (1 sentence) |
| `transaction_type` | String | **NEW**: Single-select transaction type |
| `capital_sources` | Text | **NEW**: Comma-separated capital sources (multi-select) |
| `sectors` | Text | **NEW**: Comma-separated sectors (multi-select) |
| `deal_type` | String | **LEGACY**: VC, M&A, IPO, etc. (kept for backward compatibility) |
| `deal_amount` | String | Investment amount (e.g., "$300M") |
| `investors` | Text | Key investors/acquirers |
| `strategic_significance` | Text | Why this matters (2-3 sentences) |
| `market_implications` | Text | What this signals (1-2 sentences) |
| `summary_complete` | Boolean | Was extraction successful? |
| `model_used` | String | Claude model used |
| `extracted_at` | DateTime | When extracted |

### master_list Table

Stores human-curated deals ready for publication:

| Column | Type | Description |
|--------|------|-------------|
| `company` | String | Company name |
| `investors` | String | Key investors |
| `investment_amount` | String | Deal amount |
| `transaction_type` | String | **NEW**: Single-select transaction type |
| `capital_sources` | Text | **NEW**: Comma-separated capital sources (multi-select) |
| `sectors` | Text | **NEW**: Comma-separated sectors (multi-select) |
| `deal_type` | String | **LEGACY**: Kept for backward compatibility |
| `capital_type` | String | **LEGACY**: Kept for backward compatibility |
| `sector` | String | **LEGACY**: Kept for backward compatibility |
| `project_type` | String | **LEGACY**: Kept for backward compatibility |
| `location` | String | Geographic location |
| `summary` | Text | Human-curated summary (markdown format) |
| `published` | Boolean | Ready for publishing |

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
- **`src/database/migrate_categories.py`** - Adds new category fields (transaction_type, capital_sources, sectors) to master_list table
- **`src/database/migrate_ai_categories.py`** - Adds new category fields to ai_extractions table

**Note**: These migrations have already been run if you're starting fresh. Old deals with legacy fields will continue to work thanks to backward compatibility fallbacks in the export and display logic.

## Intelligence Briefing Features

The generated deal feed (`github_site/deals/index.html`) includes:

- **Professional Layout**: Intelligence briefing style, analyst-friendly
- **Deal Cards**: Clean, scannable cards with human-curated content
- **100% Human-Curated**: Published content is exactly what you approved in triage
- **No AI Substitution**: AI drafts are never shown on the public dashboard
- **Category Badges**: Color-coded transaction type, capital sources, and sector tags
- **Search**: Real-time filtering by keywords
- **Transaction Type Filters**: Filter by funding rounds, acquisitions, contracts, etc.
- **Mobile Responsive**: Works on all devices

### Data Priority in Published Output

The export script follows this priority order:

1. **First Priority - Your Curated Data**: Company name, investors, amount, categories, and summary from the master list (what you approved in triage)
2. **Fallback for Old Deals**: For deals accepted before the curation system was implemented, shows AI-extracted data
3. **Never Shown**: RSS feed descriptions, AI company descriptions, or any data you didn't explicitly review

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

- **🔄 Workflow Optimization (Potential Cost Savings)**: Change workflow to "Curate First, AI Second" - only generate AI summaries for articles that have been approved in triage. This would save API costs by not analyzing articles that might be rejected.

  **Current workflow:** RSS → Scrape → **AI (costs $$$)** → Triage (50% rejected?) → Publish

  **Proposed workflow:** RSS → Scrape → Triage (quick scan) → **AI only for approved** → Final edit → Publish

  **Potential savings:** If you reject 50% of articles, this cuts your Claude API costs in half. However, it requires an initial quick scan without AI assistance, which may be less efficient for initial filtering.

- **Batch API calls**: Process multiple articles in parallel
- **Confidence scoring**: Flag low-confidence extractions for review
- **Custom prompts**: Tailor extraction for specific transaction types
- **Email alerts**: Notify on high-priority deals
- **Trend detection**: AI analysis of market patterns

## Questions?

For questions or issues with the AI workflow, check:
- Anthropic API docs: https://docs.anthropic.com/
- Claude model info: https://www.anthropic.com/claude
- Project README: ../README.md
