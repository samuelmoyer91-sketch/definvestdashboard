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

## Health check run (Sam: "do it now, recommendations only, don't fix")
Findings are in OPEN_ITEMS #18. Method notes for next time:
- Parse live /deals/ cards (the one card with no data attributes, Karman #2, is
  easy to miss). Reconcile by *source link*, not title: 68 legacy deals have
  blank titles.
- Check chart JSON with a browser-strict parser (Python json accepts NaN;
  browsers don't). Lazy-loaded charts only fail when scrolled into view.
- Status codes lie here: missing pages return 200 (the home page).
- Miss check: web search for ~13 notable deals, then `inspect_item.py <term>`
  to see whether a miss was never ingested, screened out, or rejected.
- Compare against the previous export to spot removals: 8 Northrop deals were
  removed today.

## Acting on it (Sam: "for #12 fix however you see fit; otherwise do all of this and push")
All shipped: `a43a5b5` (code), `da34a76` (reviewed data file), and the hourly fetch
schedule. Verified live after publish 36141883085: ITA renders, all 17 charts show
"Data through", 404 is real, Market Overview redirects, no "Date unknown" and no
"&amp;", Corporate M&A label fixed, "Other Americas" region (37), junk countries
gone, AMRC $68.6M (from £54M), Metallium $49.5M (from A$75M), 68 titles live.
Details and what's still open are in OPEN_ITEMS #18, #19 and 2+3.

Decisions I made:
- **#12 (AI currency)**: the prompt now asks for the article's own currency and
  says never to convert, because the dashboard converts at display time.
  TITLE_RULES was pulled into a constant, shared with fill_missing_titles.py;
  the rendered prompt was diffed to confirm only the two intended lines changed.
- **2025 private-capital figures NOT entered.** The sheet has no sources, and
  published figures differ roughly 15x by definition. Made the loader
  row-driven and labelled the charts "Data through 2024" instead.
- **Two title drafts rewritten in review** (RTX, Curtiss-Wright): they asserted
  figures the cards don't carry. Added Metallium A$ and Pine Bluff AR fixes
  found during that review.
- **Coverage "misses" were feed overflow**, not missing sources.
  Hourly fetch.yml (public repo, so free minutes).
- **Northrop**: 8 removals at 02:56 UTC, reason 'duplicate' (Duplicate Check
  clean-up). Left for Sam; they can be restored from /removed.
- **Push quirk**: the keychain credential helper hung, so I pushed via
  `gh auth git-credential` (gh is logged in with repo+workflow scope).

Close-out: code, data, publish, issues and logs are all pushed.
