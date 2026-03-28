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

## Files Changed
- `src/web/app.py`: removed `sync_turso()` from `get_db()` dependency
