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

## GitHub Secrets
- `TURSO_DATABASE_URL` — already set
- `TURSO_AUTH_TOKEN` — already set
- `ANTHROPIC_API_KEY` — already set
- `FRED_API_KEY` — added during this session

## Tooling Setup
- Installed **Homebrew** and **GitHub CLI** (`gh`) on local machine
- Authenticated `gh` with existing PAT (had to add `read:org` scope)
- Also added `workflow` scope to the older PAT ("Second attempt dashboard") — both tokens now have `repo` + `workflow`
- `gh` binary is at `/opt/homebrew/bin/gh` (not on Claude's default PATH — use full path)

## Test Results

### Ingest Pipeline — PASSED
- Triggered manually via `gh workflow run ingest.yml`
- Run ID: 21917089204
- Duration: 4m 36s
- All 4 steps succeeded: RSS fetch → title screen → scrape → AI summaries

### Publish Site — FAILED, then PASSED after fix
- **First run** (run ID 21917330187): site generation succeeded, but deploy step failed with `Permission denied to github-actions[bot]` — the default `GITHUB_TOKEN` lacked write access to push to `gh-pages`
- **Fix**: Added `permissions: contents: write` to `publish.yml` (commit `8d671d6`)
- **Second run** (run ID 21917467214): completed successfully in 56s — site generated and deployed to gh-pages

## Notes
- Private capital fetcher (`private_capital_fetcher.py`) reads from an Excel file not in git — it's marked `required=False` so it logs a warning and continues in CI. Charts use last locally-published JSON data.
- The `peaceiris/actions-gh-pages@v4` action handles the gh-pages branch deployment automatically — no need for subtree push.

## Open Items
- Wait for next scheduled cron run to confirm automated triggers work (ingest at 11:00 UTC, publish at 01:00 UTC)
- Consider cleaning up the older PAT ("Second attempt dashboard") — the newer "MacBook Git push" token covers everything
