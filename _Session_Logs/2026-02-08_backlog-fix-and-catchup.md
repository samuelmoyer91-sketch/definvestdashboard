# 2026-02-08 — Backlog Fix and Catchup

## Summary
Investigated and fixed a scraper bottleneck that left 179 items stuck in "new" status, then ran the full pipeline to clear the backlog.

## Key Findings
- **Root cause**: `article_scraper.py` defaulted to `limit=5` when called without arguments. Both `update_workflow.sh` and the GitHub Actions workflow called it with no arguments, so only 5 items were scraped per run — while each RSS fetch pulled in 20-40 new items.
- **Timeline**: All items found after ~Jan 15 were stuck at "new" status. Items before that date had been fully processed through scrape → AI → triage.
- **No items were actually waiting in triage** — the 108 previously scraped items had all been curated (26 approved, 82 rejected). The "179 new" items were pre-scraping, not pre-triage.

## Changes Made
- **`src/scraper/article_scraper.py` line 220**: Changed default limit from `5` to `None` (uncapped). The 1-second inter-request delay provides sufficient rate limiting, and the AI summary step has its own separate `--limit` flag for cost control.

## Pipeline Run Results
- **Scraping**: 147/179 successful (82% success rate), 32 failed (HTTP 401/403 — paywalled/bot-blocked sites)
- **AI Summaries**: 146/147 successful, 1 failed
- **146 items now in triage queue** awaiting human review

## Additional Changes
- **`update_workflow.sh` line 7**: Fixed stale path from `Claude - Defense PC Dashboard` to `PC Dashboard` (folder was renamed at some point)
- **`~/CLAUDE.md`**: Rewrote Work Style Preferences with explicit DO/DON'T rules to prevent Claude from over-asking for permission on routine tasks
- **`~/.claude/settings.json`**: Removed `Bash(* ~/Documents/*)` and `Bash(git push *)` deny rules that were blocking routine project work. `~/Downloads` and `~/Desktop` remain protected.

## Triage Results
- Approved 4 new deals (total now 30)
- Rejected 33 items (total now 115)
- ~110 items remain in triage queue for future sessions
- Published and deployed to GitHub Pages

## Config & Permissions Cleanup
- **`~/CLAUDE.md`**: Rewrote Work Style Preferences with explicit DO/DON'T rules to prevent Claude from over-asking for permission on routine tasks
- **`~/.claude/settings.json`**: Removed `Bash(* ~/Documents/*)` and `Bash(git push *)` deny rules that were blocking routine project work
- Discussed the three-layer settings architecture: global settings.json → global CLAUDE.md → project .claude/settings.local.json

## Telegram/Database Consolidation (Session 2)
- **Problem**: Telegram bot submissions went to Turso cloud DB (via Railway), but local triage read from local SQLite — two separate databases
- **Root cause 1**: `libsql_experimental` (v0.0.55) uses a deprecated sync protocol that Turso no longer supports — both locally and on Railway
- **Root cause 2**: The `TURSO_AUTH_TOKEN` stored in Railway was truncated (missing signature segment of the JWT)
- **Fix applied**:
  - Replaced `libsql_experimental` with `libsql` (v0.1.11) in `models.py` and `requirements.txt`
  - Added `LibsqlConnectionWrapper` class to bridge DBAPI compatibility with SQLAlchemy
  - Generated fresh Turso auth token via `turso db tokens create`
  - Added `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` to `~/.zshrc`
  - Updated Railway's `TURSO_AUTH_TOKEN` env var with the full token
  - Pushed to GitHub → Railway auto-redeployed
- **Verified**: Telegram submission (item #471) appeared in Turso cloud DB, readable by local `get_session()`
- **Data note**: Today's earlier pipeline run (scrape/AI/triage of 146 items) wrote to local SQLite only, not Turso. The two DBs have diverged — local has more processed data. May need a one-time sync.

## Database Sync
- Ran one-time merge of local SQLite → Turso to unify diverged databases
- Results: +78 raw items, +169 articles, +141 AI extractions, +5 master list, +44 rejected items copied to Turso
- Turso is now the single source of truth (549 raw items, 30 approved, 122 rejected)

## GitHub Actions Email Digest Fix
- Discovered `TURSO_AUTH_TOKEN` GitHub Secret was **empty** — email digest workflow has been silently failing
- Updated with the fresh full token — next scheduled run (Tuesday 9:00 UTC) should work

## Open Questions
- The 32 failed scrapes are mostly paywalled sites (Reuters, TipRanks, etc.). Could improve with alternative scraping strategies but may not be worth the complexity.
- Consider whether the GitHub Actions workflow should also uncap or use a higher limit for the AI summary step (currently `--limit 20`).
- ~110 items remain in triage queue for future sessions.
- Consider triggering the GitHub Actions workflow manually to verify the email digest works before waiting until Tuesday.
