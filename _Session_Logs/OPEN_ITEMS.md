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

## Standing context — read before designing around deal amounts

**Sam does not use this system to produce an accumulated capital total**
(stated 2026-08-08). Avoiding double-counted dollars is therefore *not* a
design constraint, and nothing should be made harder to protect one.

Confirmed in code the same day: **nothing sums `investment_amount`** — not
`generate_site.py`, not any exporter, not `/stats` (which counts rows only).
The single aggregate is `dedup.py`'s `overcount`, an advisory "estimated
double-counted dollars" hint on `/duplicates`, which is a triage aid rather
than a published figure.

Why this is written down: the roundup-splitting design was originally built
around protecting totals, including a rule that a split deal could not carry an
amount matching a sibling's. That rule was never shipped — the design changed
before it was implemented — but the rationale appears in commit messages from
2026-08-08 and would mislead anyone who reads them as current constraints.

One live consequence, left as-is by Sam's call: the focused-extraction prompt
([ai_summarizer.py:82](src/utils/ai_summarizer.py:82)) tells the model to
return "Unknown" rather than borrow another deal's figure. That is aimed at
misattribution and is still wanted. It could in principle over-apply to an
article stating the same figure for several deals ("$50M each to five
companies"), which has not been observed. Deliberately not reworded.

---

## LIVE — verified 2026-08-08

### 0. Repair the 74 European deals stored in the wrong currency
Opened 2026-08-08. The *cause* is fixed (`337d21e`); the **existing data is
not**.

Every European deal carrying an amount — 74 of them, measured from
`exports/deals.csv` — is stored as a bare dollar figure because the triage form
stripped the currency symbol before submit. Some are also off by a factor of a
million, where the magnitude went with it:

| Stored | Company | Almost certainly |
|---|---|---|
| `$100` | CSG, Bautzen | €100 million |
| `$300` | Hensoldt, Oberkochen | €300 million |
| `$3,900,000,000` | "Erail Technologies", Paris | the long-standing Exail euro bug |

Repair needs the original figure from each article, so it is a re-extraction
pass plus review, not a query. `scripts/reextract_items.py` can drive it; the
selection is deals whose `location` is European and whose `investment_amount`
carries no marker. Note the AI prompt says *"DEAL AMOUNT: Dollar value if
mentioned"*, which may itself push the model to drop or self-convert
currencies — worth checking before trusting a bulk re-extraction.

Two of these are visibly absurd on the public site right now, which argues for
fixing at least those by hand rather than waiting for a full pass.

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

### 4. Multi-deal roundups — SHIPPED 2026-08-08, and the framing was wrong

Carried in four logs as *"deal-splitting needs `master_list.item_id`'s UNIQUE
dropped, which needs a Turso table rebuild"* — the reason it was deferred three
separate times. **It needed neither.**

Shipped instead: a roundup is re-extracted once per deal it contains, each pass
told which deal to cover. Each pass is its own `raw_items` row, so it gets its
own extraction and its own `master_list` row through the unchanged accept path.
No constraint dropped, no rebuild, two additive columns.

The first plan for this *did* do the rebuild — six steps, one high-risk DDL
phase needing a migration window. Sam asked whether a simpler shape existed and
described re-entering an article with an instruction; that turned out to
dissolve the hard part entirely.

**Third time this has happened.** The `$` regex (see DONE) and the Cloudflare
token (item 11) were both carried with a stated framing that measurement or a
five-minute check disproved. A backlog entry records what someone believed at
the time, not what is true — treat the stated cause as a hypothesis.

Still open, downstream of this: whether roundups should be *detected*
automatically rather than spotted by eye (see DECISION below), and the nine
Sifted articles that fail with `stop_reason="refusal"` (item 6) — a focused
single-deal instruction may sidestep it, unproven.

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
