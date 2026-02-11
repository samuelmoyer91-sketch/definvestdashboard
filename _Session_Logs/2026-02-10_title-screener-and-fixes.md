# 2026-02-10: Title Screener & Pipeline Fixes

## Issues Identified
1. **AI prefill not working in triage** — AI extractions only covered items up to ID 548, but triage queue showed items 591–679. The `--limit 20` in the workflow wasn't keeping up with ingestion rate (185 items needed extraction).
2. **Missing queue items** — Triage query had a hard `.limit(50)` showing only the 50 most recent items. 337 unreviewed items existed but 287 were hidden.
3. **High false positive rate** — 19% overall acceptance rate (81% of triaged articles were noise). Private Equity Defense feed worst at 9% accept rate.

## Changes Made

### New: AI Title Screener
- Created `src/utils/title_screener.py` — uses Claude Haiku to batch-classify article titles as relevant/not-relevant before scraping
- Created `src/scraper/run_title_screen.py` — runner script with `--dry-run` support
- Batches 25 titles per API call for cost efficiency
- Fails open (passes items through on error or missing API key)
- Items failing screen get `status='ai_screened_out'`

### Pipeline Integration
- Updated `update_workflow.sh`: new pipeline is fetch → **screen** → scrape → AI → triage
- Added `screen` as standalone stage (`./update_workflow.sh screen`)
- Bumped AI summary limit from 20 to 100 per run

### Triage Queue Fixes
- Increased queue limit from 50 to 200 in `app.py`
- Added `ai_screened_out` status exclusion to triage query

### Config
- Updated `feeds.json` with actual Google Alert queries for all 3 feeds
- Documented acceptance rates per feed

## Results
- Retroactive screen on 338 backlog items: **193 screened out (57%)**, 145 kept
- Triage queue reduced from 338 to 145 actionable items
- 76 of those 145 have AI prefill; 69 still need AI extraction (will be covered by bumped limit)

## Feed Performance (as of 2026-02-10)
| Feed | Items | Accept Rate |
|------|-------|-------------|
| Private Equity Defense | 369 | 9% |
| New Factory Defense Products | 114 | 17% |
| Raising Capital Defense | 22 | 0% |

## Triage UI Improvements (Session 2)

### 1. Reject button in expanded view
- Added a separate `<form>` with reject button below the Accept button in the expanded review form
- No more collapsing back to collapsed view just to reject

### 2. Auto-open next item after accept/reject
- Accept and reject endpoints now find the next item in the queue and redirect to `/?open={next_id}`
- JS on page load checks for `?open=` param, auto-expands and scrolls to that item
- URL cleaned via `replaceState` so refresh doesn't re-trigger
- Helper `_find_next_triage_item()` uses same filters as the main queue query

### 3. Summary prefill simplified
- Replaced verbose "Why It Matters" + "Market Implications" prefill with just `company_description` (1-liner about what the company does)
- Label changed from "Summary (Why It Matters + Market Implications)" to just "Summary"
- Textarea rows reduced from 6 to 3

### 4. Contract/Award filtering (two-layer)
- Title screener prompt updated: routine contracts/awards now classified as NOT RELEVANT (unless involving industrial base expansion, new facility construction, or production capacity grants)
- Triage query adds outerjoin to AIExtraction and excludes `transaction_type == 'Contract/Award'`
- Contract/Award remains as a transaction type option in the form for manual edge cases

### 5. Internal Investment auto-detection
- JS: when transaction_type dropdown changes to "Internal Investment", auto-fills Investors field with Company value and updates label to show "(auto: self-funded)"
- Switching away restores the original value and label
- Export (`export_to_html_v2.py`): renders "Self-funded" for investors line when `transaction_type == 'Internal Investment'`

## Open Items
- 69 items in queue still need AI extraction — next `./update_workflow.sh ai` run will cover them with the new limit of 100
- Could consider adding pagination to triage UI if queue grows beyond 200
- Monitor screener accuracy over next few runs to tune if needed
- **Custom domain for GitHub Pages** — buy a domain (capitalfordefense.com or similar, ~$10/yr on Cloudflare/Namecheap), then add CNAME record + configure in repo settings. Claude can handle steps 2-3 once domain is purchased.
- Backfill the 25 untagged master list items (pre-taxonomy, no transaction_type/sectors)
