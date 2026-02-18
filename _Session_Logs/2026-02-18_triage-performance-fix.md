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
- Use `StaticPool` (correct pool class for SQLite/libsql); added stale-connection auto-reconnect
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

## Follow-up Fix
Initial deploy crashed — `pool_size=1` is a `QueuePool` parameter, invalid for SQLite dialect. Replaced with `poolclass=StaticPool`. Also added stale-connection detection that auto-reconnects if Turso drops the cached connection. Second push resolved the crash.

## AI-Generated Titles

Reviewed Sam's manual title rewrites on recent master list items to identify preferred titling style:
- **Structure:** [Company] [Action Verb] [Dollar Amount] [Brief Purpose]
- **Concise:** 5-10 words, never more than ~12
- **Active voice, present tense:** "Raises", "Acquires", "Builds", "Invests"
- **Include dollar amount** when known
- **Strip journalistic fluff** — no "to meet growing demand", no editorial framing
- **Use industry shorthand** — "PE Fund", "PNT", "Space Tech"
- **Always name the company** — never vague ("Startup raises..." or "Company confirms...")

### Changes:
- Added `title` column to `AIExtraction` model + startup migration
- Updated AI prompt in `ai_summarizer.py` with refined title instructions matching Sam's style
- Updated `generate_ai_summaries.py` to save the `title` field
- Updated `triage.html` to pre-populate title from AI extraction (with AI badge), falling back to raw article headline
- Existing items without AI titles still fall back to article headline (no disruption)

### Note:
Only new articles processed after this deploy will get AI-generated titles. Existing items retain their original headlines unless re-processed with `--force`.

## Open To-Dos
- **Migrate static site off GitHub Pages** — Current URL (`samuelmoyer91-sketch.github.io/definvestdashboard`) is unprofessional. Plan: Cloudflare Pages + custom domain (e.g. `capitalfordefense.com`). Requires creating a Cloudflare account, purchasing domain (~$10-15/yr), generating API token. Claude can handle the workflow migration and DNS config once account is set up.
