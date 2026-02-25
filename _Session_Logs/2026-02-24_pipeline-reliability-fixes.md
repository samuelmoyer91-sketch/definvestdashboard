# Session Log — 2026-02-24: Pipeline Reliability Fixes

## Starting Point
- User reported triage queue showing no new items despite pipeline running daily for several days
- Railway app URL confirmed: `https://capitalfordefense.up.railway.app`

---

## Root Cause Investigation

### Primary Issue: Stale Turso Replica
The Railway triage app uses a local SQLite replica of the Turso cloud database (`turso_replica.db`). The app was only syncing this replica **at startup** — meaning Railway's 24/7 uptime was working against it. Every day's ingest wrote new data to Turso cloud, but the triage UI was reading from a frozen local copy.

- The ingest pipeline was healthy (6/7 runs successful in past week)
- Items were being written to Turso cloud correctly — writes go to cloud directly in libsql embedded replica mode
- The Railway app just wasn't pulling them down

**Note on Feb 20 failure:** Turso 403 error that day was a billing incident (Railway plan lapsed, Turso temporarily blocked reads). Resolved by upgrading to paid plan. Unconnected to the main bug.

---

## Fixes Applied

### 1. Triage queue sync (PRIMARY FIX)
**Files:** `src/web/app.py`
Added `sync_turso()` before the database query in the four main read endpoints: `/` (triage queue), `/master`, `/rejected`, `/stats`. These are pages a user might navigate to directly; the item detail and edit pages don't need it since they're always reached from a page that already synced.

### 2. Investor `last_seen` logic bug
**File:** `src/web/app.py:643`
`if now > (investor.last_seen or now)` evaluates to `if now > now` when `last_seen` is None — always False. Investor timestamps were frozen at creation date. Fixed to `if investor.last_seen is None or now > investor.last_seen`.

### 3. Pipeline failure notifications
**Files:** `.github/workflows/ingest.yml`, `.github/workflows/publish.yml`
Added `if: failure()` step to both workflows that creates a GitHub issue with a link to the failed run. Added `issues: write` permission to both jobs. Previously there was no way to know a pipeline had broken without checking Actions manually.

### 4. Title screener fail-open → fail-hard
**File:** `src/utils/title_screener.py`
On Claude API exceptions, the screener was silently passing all items as relevant (flooding the triage queue with noise). Changed to re-raise the exception, which causes the GitHub Actions step to fail and triggers the notification from fix #3. The no-API-key case still warns and continues (deliberate config fallback).

### 5. Article truncation and output token limit
**File:** `src/utils/ai_summarizer.py`
- Article text truncation increased from 8,000 to 25,000 characters. News articles are typically 3–8k chars; longer pieces were being cut off mid-content, degrading extraction quality.
- `max_tokens` increased from 1,024 to 2,048. Gives Claude room to write thorough strategic analysis without truncating the JSON response.

---

## System State After Session

- Triage queue now refreshes on every page load
- Investor analytics data will be accurate going forward
- Pipeline failures will surface as GitHub issues within hours
- Title screening errors fail visibly instead of silently
- AI extraction now has full article context for longer pieces

---

## Audit Findings Not Fixed (Low Priority / By Design)

- **AI text still truncated for very long articles** (white papers, etc.) — 25k chars covers ~99% of RSS feed content; not worth further complexity
- **No API key in screener passes all items** — deliberate local dev fallback, acceptable
- **JSON parsing from Claude is naive** (markdown code block extraction) — works in practice, low risk
- **`/investors` and `/sectors` pages don't sync** — low-stakes analytics, not primary workflow pages

---

## Open Questions
- None. System healthy.
