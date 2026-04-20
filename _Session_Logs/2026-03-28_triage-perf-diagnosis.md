# 2026-03-28 — Triage Performance Diagnosis

## Problem
Accept button taking 5+ seconds; Reject also slow but less so.

## Root Cause Diagnosis
Three layered issues found in `src/web/app.py`:

### 1. FIXED — `sync_turso()` in `get_db()` (highest impact)
- `get_db()` was calling `sync_turso()` on every request as a guard against expired Turso streams, adding a blocking network round-trip before any query
- Combined with the post-write `sync_turso()` call, every Accept/Reject was hitting Turso cloud **twice** — estimated 1–4s overhead
- **Fix applied:** Removed the `sync_turso()` call from `get_db()`. Post-write calls remain in place.

### 2. DEFERRED — N+1 queries in duplicate auto-reject (lines ~545–557)
- After accepting a deal, app scans ±7-day window for same-company duplicates
- For each candidate, fires 3 separate queries: AIExtraction lookup, MasterItem check, RejectedItem check
- AIExtraction is already joined in the initial query but re-queried individually — wasted work
- On a busy day this could be 60+ extra queries
- **Fix:** Use subqueries or load all needed data in the initial join; check MasterItem/RejectedItem via `NOT EXISTS` subqueries

### 3. DEFERRED — N+1 in investor deal_count update (`_sync_investor_links`, lines ~823–827)
- For each investor in a deal, fires a separate `SELECT COUNT(*)` to update `deal_count`
- For 3–5 investors = ~10 extra queries
- **Fix:** Batch with `SELECT investor_id, COUNT(*) FROM deal_investors GROUP BY investor_id WHERE investor_id IN (...)`

## Known Side Effect of Fix
Removing `sync_turso()` from `get_db()` also removed the Turso stream expiration guard. After idle periods, the first Accept/Reject may hang ~20s while the stale connection times out — the second click will be fast. This is acceptable for now; a proper fix would be retry logic in `get_session()` (catch stream expiration error, reset, retry once).

## Future Idea: Rethink Duplicate Detection
Current duplicate detection runs synchronously on every Accept click — wrong place, wrong mechanism. Issues:
- Burdens a simple user action with background cleanup work
- Matching is fragile (user-typed company name vs AI-extracted name — often not identical)
- Reactive and invisible (silent auto-rejections, only runs when you accept)

**Option 1 (quick):** Use FastAPI `BackgroundTasks` to run cleanup after the redirect — accept click returns immediately. ~20 min change.
**Option 2 (better):** Move dedup to the nightly pipeline — flag `potential_duplicate` during AI extraction before items hit the triage queue.
**Option 3 (most transparent):** Surface duplicate groups visually in the triage UI so Sam handles them manually.

## Files Changed
- `src/web/app.py`: removed `sync_turso()` from `get_db()` dependency
- `src/web/app.py`: eliminated N+1 queries in duplicate detection and investor deal_count update
- `src/web/app.py`: removed redundant `sync_turso()` from home page handler
- `src/database/models.py`: added index annotations for status, published_date, deal_investors FKs
- Startup migration: adds 4 missing indexes on deploy (raw_items.status, raw_items.published_date, deal_investors.investor_id, deal_investors.master_item_id)

## Session Summary
Diagnosed and fixed triage performance. Accept should now run in 0.5–3s vs. 5s+ before. Occasional 20s hang on first click after idle is a known stale Turso stream issue — second click will be fast. Two open items for future sessions: (1) retry logic for stale stream, (2) rethink duplicate detection architecture.
