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

## Sectors/Technology Filter Page

Added `/sectors` and `/sectors/{name}` routes to the triage app, mirroring the `/investors` page pattern.

### Changes:
- `src/web/app.py` — Two new routes: `/sectors` (overview with deal count, total value, recent companies per sector) and `/sectors/{sector_name}` (filtered deal list for one sector). Helper functions `_parse_amount()` and `_format_amount()` for aggregating investment values.
- `src/web/templates/sectors.html` — Overview table: sector name (clickable), deal count, total deal value, recent companies, last seen date
- `src/web/templates/sector_deals.html` — Filtered deal cards per sector (reuses master list card layout)
- `src/web/templates/base.html` — Added "Sectors" nav link between "Investors" and "Statistics"
- No new database tables — aggregates directly from `master_list.sectors` comma-separated column

### Future:
- Add sector breakdown to the public GitHub Pages dashboard

## Simplified Capital Source Taxonomy

Replaced two redundant fields (transaction_type + capital_sources multi-select) with a single **Capital Source** single-select dropdown:

| Value | Covers |
|---|---|
| Seed | Pre-Series A, angel rounds |
| Venture Capital | Series A through late-stage VC |
| Private Equity | PE acquisitions, growth equity, fund raises |
| Corporate M&A | Operating company acquires another (no PE sponsor) |
| Government/Contract | Contracts, SBIR, grants, government equity stakes |
| Public Markets | IPO, SPAC, secondary offerings |
| Internal/Self-funded | Capex, facility builds from balance sheet |

### Changes:
- `triage.html` — Replaced transaction_type dropdown + capital_sources checkboxes with single `capital_source` select
- `edit.html` — Same simplification
- `app.py` — Updated accept and edit routes to accept `capital_source` (single string) stored in `capital_sources` column
- `ai_summarizer.py` — Updated prompt to output `capital_source` (single string) instead of `transaction_type` + `capital_sources` array
- `generate_ai_summaries.py` — Saves single `capital_source` string; backward-compatible with old array format

### Note:
Old deals retain their legacy field values. Decision: leave the backlog as-is — legacy fields display fine through fallback logic, no user-facing impact, not worth the busywork of batch-migrating 84 records.

## Session Summary

### What was accomplished:
1. **Triage performance fix** — Reduced accept/reject latency from ~10s to <1s by caching the Turso connection, eliminating redundant syncs, fixing N+1 queries, and scoping investor recounts
2. **AI-generated titles** — AI now writes concise analyst-style titles matching Sam's format ([Company] [Verb] [Amount] [Purpose]), pre-populated in triage form with AI badge
3. **Electronic Warfare sector** — Added as a sector option across triage, edit, and AI prompt
4. **Sectors filter page** — New `/sectors` overview (deal count, total value, recent companies per sector) and `/sectors/{name}` drill-down, accessible from nav bar
5. **Simplified capital taxonomy** — Replaced two redundant fields (transaction_type + capital_sources multi-select) with single "Capital Type" dropdown: Seed, VC, PE, Corporate M&A, Government/Contract, Public Markets, Internal/Self-funded, Fund Raise
6. **Fund Raise capital type** — Added to capture VC/PE funds raising LP capital (distinct from deploying capital)
7. **Renamed "Capital Source" → "Capital Type"** — Better label since "source" doesn't fit categories like Fund Raise
8. **Logo & favicon (B3 Corner Glow)** — Added Data Grid logo mark (3x3 grid, corner-glow opacity) to triage app header, public dashboard nav (all 23 pages), and SVG favicon
9. **Hero banner** — Full-width dark navy banner with green dot matrix (diagonal corner fade) and large green B3 logo on the public dashboard homepage

### Decisions made:
- Legacy deal data left as-is (no migration needed, fallback logic handles it)
- Cloudflare Pages migration deferred (requires account setup)
- Capital type is single-select (mixed-source deals pick the dominant type)
- Additional source URLs for deals go in the Notes field for now (no dedicated field unless it becomes a frequent pattern)
- B3 Corner Glow chosen as logo variant; green dot matrix with diagonal corner fade chosen as hero banner pattern
- Design iteration workflow: HTML mockups in `_design_drafts/`, peer screenshots in `_design_drafts/Examples/`

### Quirks discovered:
- GitHub Pages deploys from `gh-pages` branch via `publish.yml` workflow, NOT directly from pushes to `main`. Must run `gh workflow run publish.yml` after pushing site changes.
- SVG `<mask>` elements for opacity fades don't render reliably in all browsers; CSS `mask-image` with `linear-gradient` is more dependable.

## Logo & Branding (B3 — Corner Glow)

Selected the "Data Grid" logo concept — a 3x3 grid with opacity gradient radiating from the bottom-right corner ("data emerging from noise"). Variant B3.

### Changes:
- **`src/web/templates/base.html`** — Added inline SVG logo (28px) next to site title in header; added inline SVG favicon via data URI
- **`github_site/index.html`** — Added SVG logo (24px) inside nav `.logo` link; added `<link rel="icon">` for favicon
- **`github_site/favicon.svg`** — NEW: Standalone SVG favicon (navy background with B3 grid)
- **All 22 subpages** (`github_site/charts/*.html`, `github_site/deals/index.html`) — Added logo SVG in nav and favicon link
- **`_design_drafts/logo_concepts.html`** — Design exploration file with all three B variants + nav/favicon previews

## Hero Banner

Added full-width hero banner to the public dashboard homepage, replacing the plain white `.page-header` card.

### Design:
- Dark navy gradient background (`#0f1d30` → `#162f4d` → `#1e456e`)
- Green (`#88c540`) dot matrix pattern using CSS `radial-gradient`, with diagonal opacity fade from bottom-right corner toward top-left (CSS `mask-image`)
- B3 logo at 80px in green, alongside white title and subtitle
- Design iterated through multiple rounds of mockups in `_design_drafts/hero_banner.html`, referencing peer sites (Conversations with Tyler, SCSP reports) for "vibe"

### Changes:
- **`github_site/index.html`** — Replaced `.page-header` div with full-width `.hero-banner` section
- **`_design_drafts/hero_banner.html`** — Final iteration with chosen design (variant C: diagonal corner fade)
- **`_design_drafts/Examples/`** — Peer site screenshots used as design references

### Deployment discovery:
GitHub Pages was not updating after `git push` to `main`. Root cause: the public dashboard deploys via `publish.yml` workflow (peaceiris/actions-gh-pages) which copies `github_site/` to the `gh-pages` branch. Pushing to `main` alone does nothing for the live site. Fixed by running `gh workflow run publish.yml` to trigger manual deployment. **Added this to CLAUDE.md** so future sessions don't repeat the mistake.

### Next steps for branding:
- Consider using logo in email templates or reports if those are built later

## Open To-Dos
- **Migrate static site off GitHub Pages** — Current URL (`samuelmoyer91-sketch.github.io/definvestdashboard`) is unprofessional. Plan: Cloudflare Pages + custom domain (e.g. `capitalfordefense.com`). Requires creating a Cloudflare account, purchasing domain (~$10-15/yr), generating API token. Claude can handle the workflow migration and DNS config once account is set up.
- **Add sector breakdown to public dashboard** — The `/sectors` page exists on the triage app; eventually replicate on the GitHub Pages site
- **Batch-migrate legacy deals** — Low priority; 84 old records still use legacy fields, can be re-tagged to new taxonomy in a future session if needed
