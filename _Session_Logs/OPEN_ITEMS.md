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

### 1. Non-English amount expressions score zero
Found 2026-08-08 while fixing the `$` indicator (see DONE). The scorer only
understands English, singular, spelled-out magnitudes:

| Headline (all real) | Score | Outcome |
|---|---|---|
| `EDF investit 350 millions d'euros...` | 0.00 | auto-reject |
| `TKMS: 6,3 Milliarden für vier MEKO-Fregatten` | 0.00 | auto-reject |
| `Rheinmetall erhält Auftrag über 1,2 Mrd. Euro` | 0.00 | auto-reject |

`\bmillion\b` does not match "million**s**"; nothing matches `Milliarden`,
`Mrd.`, or a `€` amount. Decimal commas (`6,3`) compound it.

**Partly mitigated already:** 6 of the 7 local-language European feeds carry
`skip_relevance_filter: true`, which is why this has not shown up as missing
deals. **But `Alert: Central/Eastern European Defense` has the flag `false`** —
any local-language item on that feed is scored, hits 0.00, and is auto-rejected.
That is the live exposure.

Fix has two halves: add `€`/`£` and German/French magnitude words to
`deal_indicator_patterns` (the mechanism now exists), and decide whether the CEE
Alerts feed should carry the skip flag like its siblings.

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

### 11. Cloudflare API token — CLOSED, won't fix (Sam, 2026-08-08)
**Do not re-raise this as a security item.** Sam reviewed the evidence below and
declined rotation. That is the right call on these facts: nothing is exposed,
so this was only ever permission-tightening on a token nobody else holds.

Fold it into the next Cloudflare change if one comes up — minting a
Pages-Edit-only token is a two-minute job when you are already in that
dashboard, and pointless to schedule on its own.

**Downgraded 2026-08-08. The original framing was wrong.**

The 2026-02-19 log says the token "was briefly in `_deploy_cloudflare.py` (now
deleted, but in git history)", and every later restatement repeated that. It is
not true:

- `_deploy_cloudflare.py` appears in **no commit** — `git log --all
  --diff-filter=A` lists no such path ever being added.
- Scanning **all 291 commits, all file types** for a 40-char token-shaped
  string returns nothing.

The file was created and deleted locally before any commit. **There is no
credential exposed in the public repo**, so this is not the security item it has
been carried as for six months.

Still worth doing, for two ordinary reasons: the token is ~6 months old, and per
the 2026-02-19 log it was minted with **Pages Edit + Account Settings Read + DNS
Edit**. Only Pages Edit is needed by the workflow — `publish.yml` uses it solely
for `wrangler pages deploy`, with `accountId` passed explicitly. DNS Edit on a
long-lived token is more authority than the job requires; that permission could
repoint capitalfordefense.com.

So: rotate, and scope the replacement down to Pages Edit. Sam's task — it is
dashboard work, and credentials should not pass through here.

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
| Summary failures reported no cause | `_describe_stop` reports `stop_reason` + refusal `category` (`00925e9`) | 2026-08-08 |
| The `$` deal-indicator regex | Replaced by a named `$amount` pattern — see the note below | 07-26, 07-27, 07-28, 07-29 |

### Note on the `$` indicator — the fix was not the one described

Carried in four logs as "`\b\$\b` is too narrow, widen it". Measuring against
240 live feed items showed widening it to a bare `\$` would have **added 13
false positives and recovered zero real deals** — nine were securities-litigation
spam ("Losses In Excess Of $100,000") scoring 0.00.

The mechanism nobody had noticed: [relevance_scorer.py:157](src/utils/relevance_scorer.py:157)
makes *any* deal-indicator match exempt an article from low-score auto-rejection.
So the indicator is not worth +0.12 — it is a veto on rejection. And real deals
already match "acquisition"/"funding"/"defense", so `$` was redundant for
genuine deals and decisive only for junk.

Shipped instead: `keywords.deal_indicator_patterns`, a named-regex list, with
`$amount` = `\$\s?\d[\d,.]*\s?(?:m|bn|b)\b`. Requires a magnitude suffix, and
matches only abbreviated forms — spelled-out "million"/"billion" are literal
indicators already, so `$960 million` scores once, not twice. Net effect on 240
live items: **1 outcome change, 0 spam admitted.**

**Lesson worth keeping:** the item had been restated four times without anyone
measuring it. It read like the cheapest win on the list and was the one item
that would have made triage worse. Measure before shipping a scoring change.
