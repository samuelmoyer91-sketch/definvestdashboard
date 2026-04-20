# Session Log — 2026-04-19: Triage Performance Review & Pipeline Fixes

## Goals
- Investigate empty triage entries
- Review experimental feed performance (30-day checkpoint from 2026-03-18)
- Investigate AI writing style mismatch

---

## Fixes Shipped (commit e7e9466, 4959531)

### Empty triage entries
- **Root cause:** Scraper marked `scrape_success=True` even when `clean_text` was empty (paywalled/JS-rendered pages)
- **Fix:** Added empty-text check in `src/scraper/article_scraper.py` — returns `scrape_success=False` with reason `"empty_content"` if text is blank after extraction

### Rejection reason modal
- Replaced `confirm()` dialog with inline modal offering 5 quick-select categories + free-text
- Backend `/reject` route now accepts and saves `rejection_reason` form field
- Prior rejections (75 of 90 since March 18) had no reason recorded — this will improve future pipeline analysis

### Age filter: 7 → 365 days
- `MAX_AGE_DAYS` in `src/ingest/rss_fetcher.py` changed from 7 to 365
- Motivation: Google News RSS returns mostly old evergreen articles for broad keyword queries; the new feeds were getting 98-100% stale-filtered
- First run after this change (2026-04-20 11:00 UTC) will likely produce a larger-than-normal batch — expect queue to be fuller

### Footer email added
- `src/export/export_to_html_v2.py` — contact email added to public dashboard footer (open item from 2026-03-18)

---

## Experimental Feed Evaluation (30-day checkpoint)

### Defense M&A Transactions / Defense Tech Funding
- Both feeds ARE running correctly and finding 100 items per run
- Problem: Google News search RSS returns mostly historical content (93% older than 31 days for M&A feed)
- `tbs=qdr:w` URL parameter does NOT work on Google News RSS endpoints — Google ignores it
- After age filter change: will now surface older articles that were previously discarded
- **Note:** Google News search feeds are fundamentally different from Google Alerts — Alerts sends only new content, Search RSS surfaces evergreen results. Converting to Alerts would be the proper fix if these remain low-yield.

### Raising Capital Defense
- Correctly disabled in both feeds.json and confirmed skipped in ingest logs

### Entity-specific feeds (Carlyle, a16z/Defense VC Specialists, Defense Corporate Ventures)
- 0% accept rate over last 30 days despite producing volume
- Worth revisiting at next health check

### Overall pipeline (since 2026-03-18)
- 890 ingested, 565 AI screened out (63%), 33 accepted (3.7%), 90 rejected
- 15 auto-rejected as duplicates (feature working)
- Current queue depth: 47

---

## AI Writing Style Investigation

**Initial hypothesis (wrong):** Sam was adding "Signals continued..." market-context sentences to every accepted deal.

**Actual finding:** Those sentences came from the old template, which combined `strategic_significance` + `market_implications` into the summary textarea. This behavior was removed on 2026-03-08. Sam was NOT writing those sentences.

**Actual editing pattern (from post-2026-03-08 accepted deals):**
- Sam consistently trims AI output — cuts 2-4 sentences down to 1-2
- Cuts: redundant restatements of the deal, background filler, post-deal operational details (CEO stays, name remains), hiring/workforce numbers
- Keeps: specific product names, program names, dollar figures
- Occasionally sharpens vague language ("modernize and upgrade manufacturing capacity" → "increase production of")

**Root cause of verbosity:** Prompt says "2-3 sentences" — that's the primary driver. Likely fix: change to "1-2 sentences" and remove the instruction to explain unusual investors (generates filler).

**Status:** Fix not yet implemented — stopped to confirm with Sam before changing prompt.

---

## AI Prompt Changes (commit 547d169)

### Strategic significance
- Changed from "2-3 sentences" to "1-2 sentences"
- Removed instruction to explain unusual investors (was generating filler)
- Removed "do not editorialize" — replaced with "do not restate the deal structure or add market context"
- Pattern confirmed by comparing ai_extractions vs master_list on post-2026-03-08 accepts: Sam consistently trims verbose AI output, keeps specific product/program names, cuts restatements and background context

### Titles
- Added: "Never use county names — use the state name or abbreviation instead"
- Example fix: "Lockheed Martin Invests $150M in Pike County Facility" → "...in Alabama Facility"
- 5 existing master_list records have county names in location field (GE Aerospace/Muskegon County, Castelion/Sandoval County, Avio USA/Pittsylvania County, USAC/Sanders County, Lockheed/Pike County) — not retroactively fixed

### Location field
- Added: "Never use county names — fall back to state abbreviation only if county is the only geography mentioned"

---

## Open Items
- Consider converting experimental feeds to Google Alerts for genuinely new-only content
- Entity-specific feed performance review (Carlyle, Corp Ventures, VC Specialists)
- Optionally clean up 5 existing master_list entries with county-level locations
