# Open Items — canonical backlog

**This file supersedes the `## Open` / `## Open Items` / `## Next steps` sections
of every session log dated before 2026-08-08.** Those logs are history: they
record what was true when written and should not be edited. This file records
what is true *now*.

Every item below was checked against the code on the date in its **Verified**
field. Status meanings:

| Status | Meaning |
|---|---|
| `LIVE` | Confirmed still present in the code today |
| `EXTERNAL` | Real, but needs DB access or a third-party dashboard to confirm |
| `DECISION` | Not a defect — a product or judgment call waiting on Sam |
| `DONE` | Verified resolved. Listed so it stops resurfacing. |

**Maintenance rule:** new open items go *here*, not only in the session log.
Session logs still narrate what happened. Re-verify anything older than about a
month before acting on it — three items on this list turned out to be already
done when checked.

---

## LIVE — verified 2026-08-08

### 1. The `$` deal indicator barely matches
`config/feeds.json` (`keywords.deal_indicators` contains `"$"`) →
[relevance_scorer.py:78](src/utils/relevance_scorer.py:78) wraps every indicator
as `r'\b' + re.escape(x) + r'\b'`.

`$` is a non-word character, so `\b\$\b` requires a word character on **both**
sides. `US$1.8bn` matches; ` $100M` does not — the most common way money appears
in a headline scores lower across every feed. Carried unaddressed in four
separate logs since 2026-07-26. Smallest change with the widest reach.

### 2. `amounts_match` misses one-sided amounts
[dedup.py:194](src/utils/dedup.py:194) — returns `False` when one side has a
figure and the other doesn't. "Anduril raises $250M" never matches a write-up of
the same deal that omits the number. Fixing it means matching on company + tight
date window, which adds false positives — survivable now that removal is
reversible (`410bb9e`).

### 3. `normalize_company` prefix gap
[dedup.py:130](src/utils/dedup.py:130) — strips punctuation and legal suffixes
via `NAME_NOISE`, but has no prefix handling. From the 2026-07-29 drone/EW log.

### 4. Deal-splitting needs a schema change
[models.py:59](src/database/models.py:59) — `item_id ... unique=True` on
`master_list` means one article physically cannot yield multiple deals. This is
the root of the multi-deal roundup problem. Explicitly deferred to its own
session three times (07-26 ×2, 07-28). Needs a live Turso DDL migration, so it
runs through `migrate.yml` — see [[turso-schema-migrations]].

### 5. Accept latency is round-trip count, not slow code
`/health` on 2026-08-08: `median_pre_handler_ms` 2.1 (so *not* blocked — the
StaticPool/`async def` hypothesis from 07-29 is dead). SELECT median 106ms ×283,
INSERT 230ms ×89. Accept issues 7–16 statements → median 2810ms; reject issues 2
→ 483ms. Latency ≈ `statements × ~150ms`. Fix direction is fewer round trips
(batch the SELECTs, move `autoreject_scan`/`investors` off the click path, or an
embedded replica for reads) — not a faster handler.

### 6. Nine Sifted articles refused by the model
Opened 2026-08-08. The same 9 European VC roundups fail summarization every run
and are retried forever (the query re-selects `summary_complete == False`).

Cause is **`stop_reason: "refusal"`** — Sonnet 5's safety classifiers declining,
confirmed by run `31261208698`. An earlier `max_tokens` exhaustion theory was
**wrong**; the `max_tokens` 4096→16000 bump in `6d81bb2` was harmless but did not
fix this, and that commit's error string still says "thinking likely consumed
max_tokens", which is now misleading and should be corrected.

Next step: log `stop_details.category` in the error path of
[ai_summarizer.py](src/utils/ai_summarizer.py) — the API populates it precisely
for this case. That distinguishes a real classifier category from something odd
in the scraped Sifted content (Sifted is paywalled, so the captured text may not
be article text at all). All 9 are from the one publisher, which points at the
scrape rather than the topic.

### 7. Feed concentration
Two Google Alerts feeds are the only volatile sources — "Private Equity Defense"
swung 0% → 29% → 100% across three runs, "New Factory Defense Products" 43–80%,
while all 14 direct feeds hold 100%. The 2026-07-26 log put 82% of deals on those
two feeds; the European direct feeds have since diluted that, so **the 82% figure
is stale** and worth re-measuring before acting. The 2026-08-04 pipeline failure
was this tripwire firing correctly.

Related open question: should the feed-health tripwire warn instead of failing
the whole run?

### 8. Three staged gap-fill feeds never enabled
`config/feeds.json` — 19 enabled, 13 disabled. Still disabled from the 2026-06-09
plan: **Defense Private Credit**, **Defense Critical Minerals**, **Defense
Corporate Ventures v2**. That log noted Credit + Minerals need scorer vocabulary
added in the same commit.

### 9. Country-only locations stack on one map pin
`"UK"`, `"France"` etc. geocode to a country centroid. Fix is upstream in the
summarizer prompt (make it emit a city), not in `geocode_locations.py`.

### 10. `TRIAGE_PAGE_SIZE = 20` is an untested guess
[app.py:854](src/web/app.py:854) — one-line change to 10 (faster) or 50 (more
context). Flagged 2026-07-26, never tuned.

---

## EXTERNAL — real, but not verifiable from the repo

### 11. Cloudflare API token rotation — oldest item here
Flagged 2026-02-19, restated three times in the 2026-02-20 log, no evidence it
was ever done. The token was briefly committed in `_deploy_cloudflare.py` and
**remains in git history**. Needs a Cloudflare dashboard check, rotation, and a
GitHub secret update. Six months of exposure in a public repo's history.

### 12. Google Alerts settings unconfirmed
Each Alerts feed should be **Region = "Any region"** and **How many = "All
results"**. Asked 2026-07-26 and 07-27; never confirmed. Cheap, and relevant to
item 7.

### 13. Data-quality backlogs (need DB — use `export.yml`, the replica is stale)
- ~84 legacy-taxonomy deals never re-tagged (2026-02-18).
- 117 items dropped 2026-04-20 to the retroactive 200-char threshold
  (`scrape_success=False`, `error_message='insufficient_content'`) — never
  backfilled. Four months on, worth deciding whether to abandon.
- Exail's `$3.9B` euro conversion bug, and removing the Exail duplicate
  (2026-07-29).
- Current triage queue depth — unknown; `/api/diagnostics` needs auth.

---

## DECISION — waiting on Sam, not defects

- **Should multi-deal roundups be summarized at all**, or detected and routed
  out? Item 4 makes them *possible*; this decides whether they're *wanted*.
- Editorial "so what" framing per section (2026-03-02).
- Chart descriptions on the indicators page could tighten further.
- Map State/District dropdowns are US-congressional-district-based and stay
  US-only by nature. A country filter would be the Europe analogue — only worth
  it if Europe becomes a first-class view rather than a camera position.
- Sector breakdown on the public site (2026-02-18). `github_site/index.html`
  mentions sectors but I did not verify whether a real breakdown exists —
  **check before scheduling.**

---

## DONE — verified, stop carrying these

| Item | Evidence | Was listed open in |
|---|---|---|
| AJAX accept/reject (no page reload) | [triage.html:521](src/web/templates/triage.html:521) — `fetch()` + card removal + count update | 2026-07-26 |
| Lazy-loading charts on scroll | [indicators.html:1451](github_site/charts/indicators.html:1451) — `IntersectionObserver`, `rootMargin: 200px`, `unobserve` | 2026-03-02 |
| Migrate off GitHub Pages | Live at capitalfordefense.com via Cloudflare Pages | 2026-02-18 |
| Google News feeds → Alerts | "Defense M&A Transactions" and "Defense Tech Funding" now disabled in `config/feeds.json` | 2026-04-19 |
| Actions on deprecated Node 20 | Bumped to checkout@v7 / setup-python@v7 / upload-artifact@v7 in `6d81bb2` | 2026-08-08 |
