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

## Additional Changes (post-session-close)

### Triage noise reduction (commit c18f239)
- Speculative prompt: added "in talks", "nears", "market chatter", "likely to", "expected to", "considering", "weighing"; added "when in doubt, classify as speculative"
- Triage query: auto-exclude IPO transaction type (0% accept rate across all history)

### Accept/reject speed fix (commit a9446a3)
- sync_turso() was blocking the redirect on every accept and reject (~1-3s delay)
- Moved to FastAPI BackgroundTasks — redirect fires immediately, sync happens after

### Self-funded investor backfill (commit 2b091ec + data fix)
- AI prompt: self-funded/internal deals now return company name as investor instead of "Self-funded"
- Export: removed hardcoded "Self-funded" override for Internal Investment cards
- Retroactively updated 46 master_list.investors records and reassigned 51 deal_investor links to correct company investor records; Self-funded investor record now at 0 deals

### Triage queue sync fix (commit cf0cf5b)
- Removing sync_turso() from home route (March 28 fix) broke ingest visibility — new items from GitHub Actions never appeared in triage
- Replaced with sync_if_stale(): syncs from Turso cloud only if 5+ minutes since last sync; rapid page reloads stay fast

### Manual ingest trigger + AI failure investigation
- Triggered manual ingest at 01:43 UTC 2026-04-20 to test 365-day age filter
- Result: 253 ingested (Defense M&A: 97, Defense Tech Funding: 69 — new feeds working), 121 scraped, 65 AI summaries complete, 35 failed
- Root cause of 35 failures: MSN and paywall pages returning 3-200 chars of text (e.g. literally "MSN"), passing the empty-text check but causing Claude to return empty JSON
- Fix (commit 1df8192): raised minimum text threshold from >0 to ≥200 chars; retroactively marked 312 existing short-text items as scrape_success=False

### Triage collapsed card title (commit 4b6bb39)
- Collapsed cards were showing raw RSS headline instead of AI-generated analyst title
- Now shows AI extraction title, falls back to raw title if AI hasn't run

---

## Session Summary
Productive session covering pipeline diagnostics, a 30-day feed evaluation, prompt improvements, and numerous follow-on fixes discovered during a live ingest test. All changes committed and pushed.

## Tomorrow's Follow-Up (check after 11:00 UTC ingest run)

1. **Google News URL resolver** — did it work? Check ingest log for "→ Google News resolved to:" messages. If articles like Anduril $60B, Howmet $1.8B, CACI $2.6B show up in triage, the fix worked. If still failing, investigate further.
2. **Backfill 117 dropped items** — the real deals dropped today (scrape_success=False, error_message='insufficient_content', date_found >= 2026-04-20) can be re-scraped now that the resolver is in place. Run: `python src/scraper/run_scraper.py` or trigger a targeted re-scrape of those items.
3. **AI failure rate** — should be near zero now that 200-char threshold is in place. Confirm in ingest log ("SUMMARY: X successful, Y failed" in Generate AI summaries step).
4. **Triage queue** — should be populated with legitimate items from the new feeds. Check that collapsed card titles show AI-generated titles (not raw RSS headlines).

## Turso Resilience Fixes (2026-04-20, follow-on session)

### Morning Diagnosis

Two consecutive 11:00 UTC ingest runs failed after the prior session's changes shipped:

**Run 1 (24665207049) — "out of memory" during scrape:**
- Error: `SQLite error: out of memory` at `session.commit()` in `article_scraper.py`
- The scraper had no error handling around commits — one Turso memory error crashed the entire scrape step
- Fix shipped (prior session): wrapped commit in `except BaseException` with rollback + `_reset_turso_connection()` + reconnect

**Run 2 (24665930522) — "Internal Server Error" during RSS fetch:**
- After deploying the scraper fix, triggered a manual re-run
- New failure, different step: `ValueError: sync error: json value error, unexpected value: {"error":"Internal Server Error"}` at the very first DB operation in `rss_fetcher.py`
- Error originated in `get_libsql_connection()` → `_libsql_conn.sync()` — Turso cloud returned an HTTP 500 on the initial replica sync, which propagated uncaught up through `get_engine()` → `get_session()` → `fetch_all_feeds()` → dead process

**Key diagnostic question:** Is this a code bug or a Turso reliability problem?
- Conclusion: **both** — Turso is occasionally flaky (transient 500s, out-of-memory on writes), AND the pipeline had zero resilience to any of it. A single cloud hiccup at any step killed the whole run.
- This is distinct from the 2026-02-20 Turso 403 billing incident — that was an account issue; this is transient cloud errors from high write volume (three rapid ingest runs in 24 hours likely hit rate limits or memory pressure on the Turso side)

**Scope of the problem:** Audit revealed that `article_scraper.py` (fixed prior session) was the *only* pipeline step with BaseException handling. The other three steps — RSS fetch, title screen, AI summarizer — all had bare `session.commit()` calls with no protection. Any commit failure in any step was a full pipeline abort.

### Fixes Shipped (commit 21c3951)

`src/database/models.py`:
- Added `_sync_with_retry()` helper: 3 attempts, 5s/10s backoff, logs each attempt
- Both `.sync()` calls in `get_libsql_connection()` (initial connection + stale reconnect path) now go through retry instead of failing immediately
- `get_engine()`'s except block now also clears `_libsql_conn` (was only clearing `_turso_engine`, leaving a stale partial connection in cache)

`src/ingest/rss_fetcher.py`:
- `session.commit()` in `save_to_database()` now wrapped in BaseException → rollback + re-raise
- Per-feed loop in `fetch_all_feeds()` catches DB errors → reset connection → retry once per feed → continue on second failure (bad feed no longer aborts remaining feeds)

`src/scraper/run_title_screen.py`:
- Main `session.commit()` wrapped in BaseException → rollback + reset + single retry

`src/scraper/generate_ai_summaries.py`:
- Per-item `session.commit()` wrapped in BaseException → rollback + reset + re-add + single retry per item

**Net effect:** A transient Turso 500 now triggers a logged retry (up to 3×, 5–10s wait) at the connection layer. Mid-run commit failures trigger a reconnect and single retry, then continue rather than crashing the run. The pipeline is now consistent with the resilience model already in `article_scraper.py`.

### Google News Resolver: Experiment and Revert (commit f447bb0)

After the Turso resilience fixes, a test run (run 24666654386) completed cleanly but showed 0 successful scrapes — all 40 items failed with `google_news_unresolvable`. The resolver added in the prior session was running but could not resolve any URLs.

**Root cause:** GitHub Actions IPs are blocked or rate-limited by Google. The resolver makes an HTTP request to `news.google.com` to follow the redirect, but Google returns a captcha/blocked response from CI. The resolver returns `None` for every item, which was coded as a hard failure.

**Decision:** Revert the resolver entirely. It was a speculative feature to improve yield from the experimental Google News search feeds, but it created a worse outcome than before (hard `google_news_unresolvable` failure vs. the prior soft `insufficient_content` failure). The experimental feeds remain low-yield but the pipeline is no longer blocked by them.

**Reverted:** `resolve_google_news_url()` function and `if 'news.google.com' in url:` block removed from `src/scraper/article_scraper.py`.

### Final Verification (run 24667132412)

Post-revert run completed in **1m42s**, all steps green:
- RSS fetch: 14 new items, 389 duplicates (heavy duplication from 4 runs in one day)
- Title screen: 3 passed, 8 screened out
- Scrape: 0 successful, 3 failed (`insufficient_content` — all 3 were `news.google.com` URLs, expected behavior)
- AI summaries: nothing to process
- **No Turso errors. No crashes. Pipeline proven healthy.**

The zero-item outcome today is a feed issue (experimental Google News search feeds dominating the queue), not a pipeline issue. Tomorrow's scheduled run will process fresh items from the Google Alerts feeds via direct URLs and should populate triage normally.

---

## Session Summary
Two-day session. Day 1 (2026-04-19): pipeline diagnostics, 30-day feed evaluation, prompt improvements, multiple fixes. Day 2 (2026-04-20): diagnosed two consecutive ingest failures caused by transient Turso cloud errors, added resilience across all four pipeline steps, shipped and verified. Google News resolver attempted and reverted after proving unworkable from GitHub Actions. Pipeline confirmed healthy.

### Triage Queue State at Close-Out

Post-session investigation revealed the triage site (2 items) was correct all along. An earlier diagnostic query used a bad SQLAlchemy join (chained `.join(ArticleContent).join(AIExtraction)` without explicit ON conditions) that produced a cross-join and inflated the count to a false 232/298. Lesson: always validate ORM query counts against the exact query the app uses.

Actual DB state at close (verified against Turso using exact triage query logic):
- **2 items in triage** — correct
- 929 total scrape_success=True across all time; 242 accepted, 650 rejected — vast majority of historical items already processed
- 0 items pending scrape

**Why the "big dump" didn't happen:**
The 253-item batch ingested at 01:43 UTC was dominated by Google News URLs from the experimental feeds. Those all failed scraping (insufficient_content) without the resolver. The few non-Google-News items were mostly duplicates. The pipeline ran correctly — there simply wasn't new, scrapeable content today.

Expect a normal trickle from the Alerts feeds starting with tomorrow's 11:00 UTC run.

## Open Items
- **Google News search feeds** (Defense M&A Transactions, Defense Tech Funding): GitHub Actions IPs can't resolve `news.google.com` redirect URLs; Google ignores date filters on these feeds. Long-term fix: convert to Google Alerts for direct article URLs and genuinely new-only content.
- **Backfill 117 dropped items** from 2026-04-20 (`scrape_success=False`, `error_message='insufficient_content'`) — real deals caught by the retroactive 200-char threshold fix; can be manually re-scraped if worth recovering.
- Entity-specific feed performance review (Carlyle, Corp Ventures, VC Specialists)
- Optionally clean up 5 existing master_list entries with county-level locations
