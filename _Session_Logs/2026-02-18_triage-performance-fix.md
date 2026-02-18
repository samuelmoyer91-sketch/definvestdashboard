# 2026-02-18: Triage Performance Fix

## Problem
Accept/reject actions on the Railway triage UI (capitalfordefense.up.railway.app) were taking ~10 seconds per click.

## Root Causes Identified
1. **`conn.sync()` on every DB connection** — Each `get_session()` call created a new libsql connection and synced the local replica with Turso cloud (~2-3s network round-trip each, multiple times per request)
2. **`_find_next_triage_item()` re-ran full triage query** — Heavy query with joins and subqueries after every accept/reject (~1-2s)
3. **N+1 queries on home page** — After redirect, the `/` route loaded 200 items then ran 2 individual queries per item (400 extra DB calls) to fetch article_content and ai_extraction (~2-4s)
4. **`_sync_investor_links` scanned ALL investors** — Iterated entire investors table to recount deals on every accept
5. **`sessionmaker()` recreated on every call** — Minor but wasteful overhead

## Changes Made

### `src/database/models.py`
- Cache single libsql connection in `_libsql_conn` global; only call `conn.sync()` once on first connection
- Added `pool_size=1` and `pool_pre_ping=False` to engine config
- Added `sync_turso()` helper — explicitly syncs replica after writes only
- Cache `sessionmaker` in `_session_factory` global

### `src/database/__init__.py`
- Export new `sync_turso` function

### `src/web/app.py`
- Added `sync_replica_on_startup()` event to sync replica when app boots
- Home page (`/`): replaced N+1 loop with SQLAlchemy `joinedload()` for `RawItem.article` and `RawItem.extraction`
- Accept route: removed `_find_next_triage_item()` call, just redirect to `/`; added `sync_turso()` after commit
- Reject route: same — removed next-item lookup, added `sync_turso()` after commit
- Edit save route: added `sync_turso()` after commit
- Email action routes: added `sync_turso()` after commits
- `_sync_investor_links()`: only recount `deal_count` for affected investors, not the entire table

## Expected Impact
~10s per click → under 1 second

## Deployment
Committed and pushed to main. Railway auto-deploys from main branch.
