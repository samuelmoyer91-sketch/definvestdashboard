# Session: GitHub Actions Automation — 2026-02-11

## Goal
Automate the full ingest and publish pipeline via GitHub Actions so the only manual step is triaging deals on Railway.

## Changes Made

### New Workflows
- **`.github/workflows/ingest.yml`** — Daily 6 AM ET (11:00 UTC)
  - Fetch RSS → title screen → scrape → AI summaries (limit 100)
  - Added title screening step (was missing from old workflow)
  - Dropped email digest step (triaging via Railway now)
- **`.github/workflows/publish.yml`** — Daily 8 PM ET (01:00 UTC)
  - Runs `generate_site.py` (FRED + Yahoo Finance + chart generation + deal export)
  - Deploys `github_site/` to gh-pages via `peaceiris/actions-gh-pages@v4`
  - Replaces manual `git subtree push` approach

### Deleted
- **`.github/workflows/process-feeds.yml`** — Replaced by the two new workflows above

### Code Fix
- **`generate_site.py`** — `check_api_key()` now detects non-interactive environments (`sys.stdin.isatty()`) and auto-continues instead of hanging on `input()` in CI

### README Updates
- **`1 - README.md`** — Rewrote workflow section to describe automated pipeline, updated architecture table to show GitHub Actions instead of local pipeline, updated "What Gets Updated" to reflect daily cadence

## GitHub Secrets Required
- `TURSO_DATABASE_URL` — already set
- `TURSO_AUTH_TOKEN` — already set
- `ANTHROPIC_API_KEY` — already set
- `FRED_API_KEY` — **needs to be added** for the publish workflow

## Verification Steps
1. Push to main
2. Manually trigger ingest workflow from Actions tab
3. Manually trigger publish workflow from Actions tab
4. Verify triage queue has new items
5. Verify GitHub Pages site updated
6. Wait for next scheduled run to confirm cron works

## Notes
- Private capital fetcher (`private_capital_fetcher.py`) reads from an Excel file not in git — it's marked `required=False` so it logs a warning and continues in CI. Charts use last locally-published JSON data.
- The `peaceiris/actions-gh-pages@v4` action handles the gh-pages branch deployment automatically — no need for subtree push.
