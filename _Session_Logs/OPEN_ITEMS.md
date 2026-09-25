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

## LIVE — verified 2026-08-08; 0/5/6 re-verified 2026-08-12; 0/2/3/6 on 2026-09-24

### 0. European deals stored in the wrong currency — PARTLY DONE 2026-09-24
The *cause* was fixed 2026-08 (`337d21e`), and every form now shares one
formatter (`_currency_input.html`). **Data repair, round 1, done 2026-09-24:**
31 deals corrected via `scripts/fix_currency_amounts.py` from
`scripts/data/currency_fixes_2026-09-24.json` (old and new values kept there,
so it can be reversed). Verified by re-export: 31 of 31 match.

How they were found: the curated **titles still carried the currency**
("Hensoldt Invests €300M…"). Of 48 deals whose title names a non-USD currency
but whose amount was stored as `$`:
- 24 had lost only the symbol; 5 had lost the magnitude too (`$300`, `$100`,
  `$1`, `$4.4`, `$165`). All 29 were fixed.
- **17 were correct already**: someone had converted them to USD by hand
  (e.g. €350M stored as $401.5M). **Do not add a symbol to these**; that would
  double-convert them. They are the rows in the fixes file's source scan
  marked MISMATCH.
- 2 were wrong in other ways: EDF (#699) was stored 10x low, and Airbus (#107)
  was stored as `$530,000` instead of `$530,000,000`. Both fixed.

**Still open, round 2:** 53 European-located deals with a `$` amount and
**no currency in the title**. Some of them really are USD deals. This needs
the article: re-extract with `scripts/reextract_items.py` and have Sam review
a list of old versus new. The prompt says *"DEAL AMOUNT: Dollar value if
mentioned"* and Sam wants that wording kept, so check whether re-extracted
amounts keep their € before trusting them.

Seen in passing: #647 "Erail Technologies" is a misspelled duplicate of the
Exail/Thales deal (#795, #506, and a $4.5B variant #502).

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

**Mitigated:** the 6 local-language European feeds carry
`skip_relevance_filter: true`, which is why this has not shown up as missing
deals.

**Correction, 2026-09-24:** this entry used to call the CEE Alerts feed (flag
`false`) "the live exposure". Checked against 59 ingest logs (Jul 28 – Sep 24):
that feed produced **9 items in total and auto-rejected none**. Its query is
deliberately English (see its `notes` in `config/feeds.json`), so the flag
was never the problem and was NOT changed. The real finding is that the feed
is **nearly silent**; widening its query is the lever if CEE coverage matters.

Remaining fix, if wanted: add `€`/`£` and German/French magnitude words to
`deal_indicator_patterns` (the mechanism exists). Low value while the skip
flags cover the local-language feeds.

### 2+3. Duplicate matching misses most real duplicates — measured 2026-09-24
Items 2 (one-sided amounts) and 3 (name variants) were the visible edges
of a bigger gap. Sam asked why the Published Dup Check "hasn't come up with
anything new". It runs fine, but on today's 925 deals it lists 2 clusters:
Hensoldt, a real duplicate that only became matchable after the currency
repair, and Northrop Utah vs Florida, a false alarm because neither has an
amount. Meanwhile the rules catch **1 of 27** duplicate pairs verified by hand
over Jul 22 – Sep 16. The reasons, in order of frequency:
- **Company name variants** ([dedup.py:130](src/utils/dedup.py:130)):
  "Raytheon" / "Raytheon (RTX)", "Stoke Space" / "Stoke Space Technologies",
  "L3Harris" / "L3Harris Technologies", a missing European suffix
  (SA/GmbH/mbH), and a typo ("Erail" for Exail).
- **One card has no amount** (GoPro/Starman, Heven, Duotech, Perpetua).
- **Converted currencies drift past the 5% tolerance** (ICEYE €1B vs
  $1.16B, Neuraspace €15.6M vs $18M).
- **The same deal re-reported after the 30-day window** (Rheinmetall €350M
  Bavaria, 51 days; Park Aerospace $65M, 55 days).

The pre-triage Possible Dups bucket uses the same helpers, so these are also
exactly the duplicates that get past triage. The page staying empty follows
from that. It is not evidence that it works.

**Prototype** (scratch, not shipped): token-subset/typo name matching, city
as a tie-breaker (different cities = different deal unless the amounts are
identical, e.g. GE/CPP buyer vs target HQ), 12% tolerance when either
amount was converted, one-sided amounts allowed with the same place + a
similar headline, and 60 days when amount and place match. Result: 22/27 real
pairs caught, 2/19 known-distinct pairs flagged (Rheinmetall Neuss vs
Nordhessen; Iten expansion vs NP Aerospace buying Iten). A full scan
suggests 40–50 duplicate groups in the published data (~5%).

Page problems Sam raised: no "not a duplicate" dismissal (judged pairs
stay forever), a table that overflows on phones (the Remove buttons exist
but are tiny), and a noisy "94 companies judged distinct" list.

**SHIPPED 2026-09-25 (Sam: "do all of this").** `dedup.find_pairs`/`match_pair`:
24/26 verified pairs, 0/14 false matches, 42→40 clusters on 945 deals, 15 ms. Tuning
notes are in the constants' comments. The remaining misses are by design: CSG/NVD
(one amount, dissimilar headlines) and Perpetua (two towns given for one plant).
"Not duplicates" stores pairs in `dup_dismissals`. **Sam's one-time clear-out of
~40 groups is pending.**

**Previously, Sam's call on 2026-09-24: bare minimum for now.** Shipped only the phone
layout (`abe2056`). NOT built, and the proposal stands: the matching overhaul
above (tune out the 2 false flags first; it also changes what the pre-triage
bucket holds back), a "Not a duplicate" dismissal (needs a small new table),
and a one-time clear-out of the ~40–50 groups. The "judged distinct" list was
deliberately kept: until matching improves, it is the only place same-name
misses like the L3Harris Rhode Island cards show up.

### 5. Accept latency is round-trip count, not slow code
`/health` on 2026-08-08: `median_pre_handler_ms` 2.1 (so *not* blocked — the
StaticPool/`async def` hypothesis from 07-29 is dead). SELECT median 106ms ×283,
INSERT 230ms ×89. Accept issues 7–16 statements → median 2810ms; reject issues 2
→ 483ms. Latency ≈ `statements × ~150ms`. Fix direction is fewer round trips
(batch the SELECTs, or move `autoreject_scan`/`investors` off the click path)
— not a faster handler.

**Correction, 2026-08-12:** an earlier version of this item suggested "an
embedded replica for reads". The app *already runs one* — that is what
`turso_replica.db` is. Reads measuring 106ms means they are not being served
locally despite it, so adding a replica is not the fix and would be a dead
end. Why a local replica still costs a full round trip per SELECT is itself
worth understanding before optimising anything else here.

### 6. Refusals are `category=bio`, and NO fallback fixes them — root cause found 2026-09-24
Settled 2026-08-12. The `stop_details.category` logging added on 08-08 paid off:

```
stop_reason=refusal, category=bio
explanation=API integrators: you can reduce refusals ... configuring a fallback model
```

Anthropic's message points at a fallback model. **Tested, and it does not
work** — do not spend time on it again:

| Approach | Result |
|---|---|
| Server-side `fallbacks` param | **400** — `'claude-sonnet-5' does not support the fallbacks parameter`; `allowed_fallback_models = []` on both beta headers |
| Retry on `claude-sonnet-4-6` | refuses, `category=bio` |
| Retry on `claude-opus-4-8` | refuses, `category=bio` |
| Retry on `claude-haiku-4-5` | answers, but the answer is *"Unfortunately, I cannot extract…"* |

So every model declines the same content. A client-side fallback would refuse
three times and cost more. **Decision: build no fallback.**

**The open question, and the more promising lead:** the test article is
*"AI, dual use and spacetech: the new stars of debt funding"* — a European VC
funding roundup, which has no business tripping a *biology* classifier. That
suggests the text being sent is not the article. Sifted is paywalled, so the
scrape may be capturing something else entirely, which would also explain why
it is always the same articles.

**ROOT CAUSE FOUND 2026-09-24 — it is the scrape, and it is Sifted.**
`inspect_failing_text.py` finally ran (run 36083257006; `gh run view --log`
reads it fine). 29 articles are failing: **27 are `Direct: Sifted`**, plus one
each from Private Equity Defense and New Factory Defense Products. Every Sifted
article has the same shape: a readable headline and first paragraph, then
**thousands of characters of paywall-scrambled text**:

```
ZuriQ ... has raised a $25.5m seed round to develop a new architecture for
quantum chips...Plf zahss fmk hvf ud Xbyqwjtblrda, r Hvyik-kfgah TV lpymsmo...
```

The model's safety filter reads that cipher-like text as a possible attempt to
hide something and refuses; `category=bio` is a red herring. The readable lead
nearly always carries the deal (company, amount, investors).

**Two consequences, both worse than a blank card:**
1. **Refused deals are hidden from triage, silently.** A refusal stores an
   empty `ai_extractions` row, and the queue's all-Unknown filter
   ([app.py `_triage_queue_items`](src/web/app.py)) removes it. Missing from
   master as of today: Uforce ($4bn-valuation drone round) and The Exploration
   Company ($450M). ZuriQ got in through another source.
2. **Refused items are retried every day, forever.** The pile grows as Sifted
   publishes: 9 (Aug 10), 12 (Aug 25), 19 (Sep 9), 29 (Sep 24). Daily
   extraction spend rose from ~$0.3–0.5 (July) to ~$1.0–1.1; roughly half of
   today's is the retries.

**Fix BUILT 2026-09-24 (verify after the first live run):**
- `src/utils/text_quality.py::readable_part` finds the point where the text
  turns into random letters (vowel share of Latin letters, word-level change
  point, snapped to a sentence end) and the summarizer sends only the part
  before it. Tested: cuts 0 of 1,637 stored articles and 0 of 32 live
  EN/DE/FR articles; cuts all 6 refused samples and the 9 of 14 live Sifted
  articles that are scrambled, exactly at the scramble. Cyrillic, Hebrew and
  Arabic are ignored rather than read as consonants.
- A refusal sets `RawItem.status = 'extraction_refused'`
  (`models.EXTRACTION_REFUSED`): no daily retries, and triage shows the card
  with a notice instead of hiding it. A later clean extraction resets it to
  `scraped`.
- **Outcome, same day:** the manual ingest after deploy cut refusals from 29 to
  9. All 20 trimmed articles extracted, and the 9 failures were ones v1 had
  not trimmed. Those Sifted pages follow the scramble with readable "related
  articles" teasers, so v1's assumption that the scramble runs to the end
  failed. **v2** (`d4f38e2`) finds the scramble anywhere: vowel-share
  windows detect it, and a rare-letter-pair change point places the cut.
  Rare pairs are never used for detection, because they are common in
  Polish/Czech. Re-run with `reextract_items.py --refused --apply`:
  **7 of 9 recovered** (The Exploration Company $450M, Open Cosmos €300M,
  Exein $270M, DTCP €455M, Uforce, Loft Orbital, ElevenLabs).
- **Still refused, shown in triage:** #15054 DecisionPoint (a BLOX-CMS news
  page; v2 trimmed 2.9k chars of what looks like encoded boilerplate, and it
  was still refused) and #20594 (a Sifted drone-boat story, not trimmed).
  Not investigated further — Sam asked for the bare minimum.
- **If refusals climb again:** run `inspect_failing_text.py` first. Every
  refusal seen so far was input text, not model behaviour.

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


### 16. Private-capital charts stop at 2024 — verified 2026-09-25
The live `vc_defense.json`, `ma_defense.json` and `public_defense_companies.json`
all end at 2024-12-31. They come from a hand-maintained Excel file
(`src/data_fetchers/private_capital_fetcher.py`), so nothing refreshes them
automatically, and their `last_updated` stamp (the time the fetch ran) says
"today". Needs the 2025 figures entered once they're published. The FRED and
market series are current (monthly through Jul/Aug, quarterly through Q2,
daily through yesterday).

### 17. Deals page is 2.3 MB of HTML — verified 2026-09-25
`/deals/` renders all 945 cards in one page. That's fine on wifi and slow on a
phone, and it grows by ~150–180 deals a month. Not urgent. Worth watching as
part of a site health check.

### 18. Public-site health check findings — verified 2026-09-25, ACTED ON same day (see below)
Full check against the live site; details in `_Session_Logs/2026-09-25_site-health-check-design.md`.
- **ITA chart broken** on both Indicators ("Data unavailable") and Market Overview:
  `data/ita.json` has one `NaN` row (2021-09-24), which browsers reject as JSON.
  `finance_fetcher.py` has no NaN guard. The file was clean on 2026-07-03.
- **Market Overview page**: not linked from anywhere, ITA/comparison charts broken,
  links to a `defense-spending.html` that doesn't exist.
- **Soft 404**: any missing URL serves the home page with HTTP 200 (there is no 404.html),
  so broken links are invisible.
- **Display defects**:
  - AMRC #581 shows "$54" (should be about £54M).
  - The "Corporate M&A" filter label shows as `corporate-m&a` on 163 deals:
    `slugify` keeps "&", but the label map expects `corporate-m-a`. One raw
    `intelligence` sector entry too.
  - Region filter puts Canada (27) under "Other" and lists junk countries "Uda" and
    "United Kingdon".
  - 6 undated deals (Saronic $600M, Mach $300M, Cambridge Aerospace $300M…) sort to
    pages 94–95 of 95.
  - 4 headlines show a literal "&amp;".
  - 68 early deals have no curated title and show the raw article headline.
- **Home page scope text is outdated**: it says U.S.-only and "excludes foreign
  defense markets"; about a third of deals are non-US (Europe alone 187).
- **The AI still writes "$" for euro amounts**: Klaipeda #956's extraction returned
  `$100M` for "EUR100 Million". This comes from the "DEAL AMOUNT: Dollar value" prompt
  wording, which Sam chose to keep in August. DECISION.
- **Coverage**: 9 of 13 notable Aug–Sep deals are on the site. Never ingested:
  Defense Unicorns $136M Series B, Arxis's StratEdge and Schatz Bearing add-ons.
  Aurelius–Marshall Aerospace was ingested and rejected by Sam.
- **9 deals removed on 2026-09-25**: Hensoldt #649 (a real duplicate) plus 8 distinct-
  looking Northrop Grumman deals (#212, #437, #557, #692, #739, #760, #884, #930).
  Sam to confirm intent; they can be restored from /removed.
- **Housekeeping**: 6 stale open "pipeline failed" issues (#1, #2, #5–#8). The publish
  cron "01:00 UTC" starts at a median 4.5h late (max 11h).
- **Healthy**:
  - All pages, data files and domains up; certificate valid to Nov 14.
  - 30/30 publishes succeeded.
  - Site ↔ database 945/945 exact.
  - FRED and market data current.
  - Filters, search, paging and map all work; 16/17 charts render.
  - Phone layouts fine; source links 58/60 live.
  - Few false positives (6, all legacy Jan–Feb).
- Map: 90 of 868 pins (10%) sit on a country or state centre (see #9).

**Outcome, 2026-09-25 (commits `a43a5b5`, `da34a76`):**
- Fixed and verified: the ITA chart (NaN rows skipped, all data files refuse NaN),
  "Data through" on every chart, date fallback + sort (no "Date unknown"),
  filter labels, the "Other Americas" region, single escaping, home page scope
  text, the real 404 page, Market Overview retired (301 to Indicators), and the
  prompt keeping original currencies. 73 reviewed data fixes: 68 titles, AMRC
  £54M, Metallium A$75M, three location typos. 6 stale issues closed.
- **Northrop removals**: all 8 went at 02:56 UTC as reason 'duplicate' — Duplicate
  Check clean-up of a false alarm, it seems. Not restored; Sam to decide.
- **Still open:**
  - The 2025 private-capital figures. The spreadsheet has no sources, and
    published figures differ widely by definition (JPM/PitchBook broad $55B for
    2021 vs Crunchbase narrow ~$3B). The loader now reads any new row, and the
    charts say "Data through 2024".
  - Page weight (#17).
- The coverage misses were feed overflow, not missing sources. See #19.

### 19. Busy feeds overflowed their daily read — fix shipped 2026-09-25, verify
PR Newswire A&D, Pulse 2.0 and Defence Industry Europe returned only new items on
10 of 10 days: each lists its latest 10–20 items and publishes more per day, so a
once-a-day read missed the rest. Both Arxis add-ons (Sep 3, on PR Newswire and
Pulse 2.0) were lost that way. (Defense Unicorns $136M was a January deal from
before those feeds existed, not a current gap.) `fetch.yml` now reads all feeds
hourly at :17 (skipping 11:00, when the ingest reads them), sharing a concurrency
lock with the ingest. The first manual run, after an 11.5h gap, showed Pulse 2.0 no
longer overflowing (16/20 already seen) but PR Newswire still 20/20 new, which is
why the schedule went hourly rather than every 4h. **Verify in a few days:** those three feeds should start showing
duplicates in their "Saved N new items, skipped D duplicates" log lines. If they
still come back all-new, read more often or page deeper (WordPress `?paged=2`).
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
- The Exail duplicate still needs removing (2026-07-29). Its `$3.9B` figure
  is **explained** — see item 0; the triage form was discarding the euro
  marker. Repairing it is part of that backfill, not a separate puzzle.
- Current triage queue depth — unknown; `/api/diagnostics` needs auth.

---

## DECISION — waiting on Sam, not defects

- **Should multi-deal roundups be summarized at all**, or detected and routed
  out? Item 4 makes them *possible*; this decides whether they're *wanted*.
- **Phone triage, next round** (2026-09-24). The basics shipped (see DONE). Not
  yet built, in order of value:
  - **C.** Show the AI summary sentence on the closed card, and add a "Quick
    accept" for cards whose AI fields are already right. Sector and capital
    type could become tap-to-toggle tags instead of 33 checkboxes.
  - **D.** Swipe to accept/reject. Needs an undo first — nothing can be undone
    today — so it only makes sense after C.
  Sam to decide after a few evenings on the new layout. (2026-09-24: Sam
  passed on C for now, even though 54% of accepts go through untouched.)
- **Debt capital type** (added 2026-09-24). Only NEW extractions and hand
  edits use it: existing debt deals (e.g. "Airbus Secures €3B EIB Loan") keep
  their old tags until someone backfills them. Transaction type still has no
  debt option, so a loan is labelled with the nearest existing type.
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
| Triage unusable on a phone | Phone layout via `@media (max-width: 640px)` in `triage.html` + `base.html`; Accept/Reject pinned to the bottom of an open card; the "$ €" display fixed. Measured at 375px wide | 2026-09-24 |
| Accept/Reject waited on the server | Card leaves on tap; comes back with a message if the save fails (`saveDecision` in triage.html) | 2026-09-24 |
| "Self-funded" investor retyped by hand | Triage pre-fills the company's own name (Sam overrode "Self-funded" 21/21 times) | 2026-09-24 |
| "Unknown" location looked up by hand | Prompt now gives the company HQ when known with confidence (was hand-filled 29/33 times) | 2026-09-24 |
| Possible Dups unusable on a phone | Rows stack as cards under 640px; desktop unchanged | 2026-09-24 |
| Published Dup Check unusable on a phone | Same stacked-card layout, full-width Remove (`abe2056`) | 2026-09-24 |
| Published-site health check #18 fixes | See #18 outcome; live-verified after publish | 2026-09-25 |
| Duplicate matching caught 1/27 | Reworked matcher + "Not duplicates" (items 2+3) | 2026-09-25 |
| Stale "pipeline failed" issues | Closed #1, #2, #5–#8 with a note | 2026-09-25 |
| No way to retry refused articles | `reextract_items.py --refused [--apply]` | 2026-09-24 |
| Currency code copied per page (#14, #15) | One shared `_currency_input.html` now used by triage, item-detail and edit. Item-detail no longer strips symbols; edit no longer turns `C$`/`A$` into `C`/`A` | 2026-09-24 |

### Multi-deal roundups — shipped 2026-08-08, and the framing was wrong

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
