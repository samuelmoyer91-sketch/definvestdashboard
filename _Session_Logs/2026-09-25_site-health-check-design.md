# 2026-09-25 — What a public-site health check should cover

Sam asked what the right elements of a health check of capitalfordefense.com
would be. I answered in chat and did not run a full check. Quick probes to
ground the answer:
- All 5 pages and 20 data files return 200; www and pages.dev resolve.
  Today's publish ran at ~05:35 UTC against a 01:00 cron; GitHub delays
  scheduled runs.
- **Freshness stamps mislead:** every data file's `last_updated` is when the
  fetch ran, not the newest data point. That is how the Feb–Jul chart freeze
  went unnoticed. The newest points: FRED monthly Jul/Aug 2026, quarterly Q2,
  market daily Sep 24. **Private-capital series end 2024** (OPEN_ITEMS #16).
- Live deals page: 945 cards, consistent with yesterday's 925-deal export plus
  last night's accepts. 870 have a region, 925 have sectors. The map has 868
  points. The page is 2.3 MB (OPEN_ITEMS #17).
- The repo's `github_site/` is frozen at March (468 deals). The live site is
  rebuilt by `publish.yml` and never committed back, so checks must hit the
  live site.
