# 2026-08-08 — Post-vacation review + quick-win maintenance

Sam back from ~8 days away. Broad survey of pipeline, triage app, and site,
then the quick-win fixes. The substantive accept-latency work is deferred to
its own session.

## Survey findings

**Healthy:** ingest ran all 8 days (7/8 succeeded), publish ran daily,
capitalfordefense.com 200 in ~0.19s, Railway app up 7.9d on HEAD (`c3136794`)
with no restarts, all 14 direct feeds at 100% scrape rate, volume steady at
110–166 new items/day.

### 1. The 2026-07-29 accept-latency question is answered

The instrumentation left running on 7/29 collected real triage data over the
vacation. Read from `/health`:

- `median_pre_handler_ms` = **2.1** — the app is NOT blocked. This kills the
  leading hypothesis from the 7/29 log (single `StaticPool` connection +
  `async def` routes doing blocking I/O). Not it.
- The time is per-statement round-trips to Turso:

  | verb | count | median |
  |---|---|---|
  | SELECT | 283 | 106ms |
  | INSERT | 89 | 230ms |
  | UPDATE | 28 | 121ms |

- accept issues 7–16 statements → median **2810ms**, worst 5616ms.
  reject issues 2 → median 483ms.

So latency ≈ `statement_count × ~150ms`. The 9→4 write reduction (`de1ab1e`)
helped; the remaining **283 SELECTs** now dominate. The fix direction is fewer
round trips (batching, or an embedded replica for reads), not a faster handler.
Deferred to its own session.

### 2. Nine articles stuck in a permanent daily retry loop — FIXED

The same 9 European VC roundup articles failed summarization on *every* run.
Identical first-9 list on 8/7 and 8/8; exactly 9 failures on all four runs
checked (8/4, 8/5, 8/7, 8/8) while success counts varied (22/28/27/36).
They are retried forever because `generate_ai_summaries.py` re-queries anything
with `summary_complete == False`.

**Root cause:** `ai_summarizer.py:129` used `next(...)` with no default. The
Sonnet 5 migration (2026-07-08) applied the safe-default fix to
`title_screener.py:155` but **not** to the summarizer.

`StopIteration` stringifies to `''` — which is exactly why the log read
`⚠️  Error generating AI summary: ` with nothing after the colon. Reproduced
locally, character for character.

**Trigger — CORRECTED after verification run `31261208698`:** the hypothesis
below was **wrong**. With the improved error message the real cause is
`stop_reason: "refusal"` — Sonnet 5's safety classifiers declining these 9
outright, not thinking exhausting the token budget.

> ~~`max_tokens=4096` with adaptive thinking. Thinking and the answer share that
> budget; on long multi-deal roundups thinking consumed it all.~~

The `max_tokens` 4096→16000 change is harmless (it is the documented
non-streaming default, and `max_tokens` caps rather than spends) but it fixed
nothing. The error string committed in `6d81bb2` still ends "thinking likely
consumed max_tokens", which is now misleading and needs correcting.

What *did* work is the error-message change: a month of empty-string errors
became a precise cause in one run. Next step is logging
`stop_details.category`. All 9 are Sifted articles — one paywalled publisher —
so the scrape is as likely a culprit as the topic. Tracked as item 6 in
[OPEN_ITEMS.md](OPEN_ITEMS.md).

**Fixes applied:**
- `max_tokens` 4096 → 16000 (the documented non-streaming default). `max_tokens`
  is a cap, not a spend — this costs nothing on calls that already succeed.
- `next(...)` given a `None` default; a missing text block now raises a real
  error naming `stop_reason`.
- Error log now prints `type(e).__name__` — the absence of that alone is what
  made this undiagnosable for a month.
- Error path now returns real `usage` tokens instead of hardcoded 0. Failed
  calls were billed but recorded as zero, so `/costs` under-reported. The
  caller already accumulates from this dict, so one fix covers both.

**Note:** this stops the crash and the ~$0.50/day burn. It does NOT solve the
underlying multi-deal-roundup problem — one row still can't represent five
deals. See [[multi-deal-announcements]]. Open question below.

### 3. Feed fragility is concentrated in the 2 Google Alerts feeds

All 14 direct feeds scrape at 100%. The two Alerts feeds are the volatile ones:
"Private Equity Defense" ranged 0% → 29% → 100% across three runs;
"New Factory Defense Products" 43–80%. The 8/4 pipeline failure was this
tripwire firing correctly (29%, below the 30% floor), which opened issue #5.

Structural risk, since deal flow rests on those two feeds. Not addressed.

### 4. Actions Node 20 deprecation — FIXED

All four workflows pinned `actions/checkout@v4` + `actions/setup-python@v5`
(+ `upload-artifact@v4` in export.yml), all forced onto Node 24 with a warning.
Usage is entirely vanilla (bare checkout; `python-version` + `cache: pip`), so
bumped all three to current majors (v7). YAML validated.

### 5. Sonnet 5 intro pricing ends 2026-08-31

$2/$10 → $3/$15 per MTok, a 50% increase, in three weeks. Confirmed against the
pricing table in `src/utils/pricing.py:13`, which already carries the note.
Worth a cost check before month end.

## Not done / needs Sam

- Triage backlog depth unknown — `/api/diagnostics` requires auth. At ~90 net
  new items/day for 8 days, expect several hundred pending, but that's
  arithmetic, not a measurement.
- 3 open bug issues (#5 from 8/4; #1 and #2 stale from 2026-04-20) — not closed,
  outward-facing.
- `admiring-cerf` branch + worktree from 2026-01-05 — not pruned, deletion.
- Changes not pushed. Real verification of the summarizer fix is the next ingest
  run: the 9 stuck items should clear and `SUMMARY: N successful, 0
  failed/incomplete` should replace the standing 9.

## Open questions

Moved to [OPEN_ITEMS.md](OPEN_ITEMS.md), which is now the canonical backlog and
supersedes the `## Open` sections of every log before today. Open items from
this session are tracked there as items 5, 6, and 7.

## Backlog consolidation (same session)

The deferred items were scattered across ~31 logs, restated rather than
resolved, with drifting status. Built `OPEN_ITEMS.md`: every item verified
against current code, with `file:line` evidence and a verified-on date.

Three items carried as open turned out to be **already done** — AJAX
accept/reject (`triage.html:521`), lazy-loading charts
(`indicators.html:1451`), and the Google News → Alerts migration. That is the
argument for the file: without verification, the list was actively misleading.

---

# Roundup splitting — shipped (same session, evening)

One article could produce at most one deal. Roundups mooshed several into one
card. Now a roundup can be re-done as N focused deals.

## The approach changed once, and that was the important part

The first plan dropped `master_list.item_id`'s UNIQUE so one article could own
N deals. That needs SQLite's 12-step table rebuild on Turso — the operation
that silently failed during the soft-delete migration — across six steps with
one high-risk DDL phase and a migration window. It was approved.

Sam then asked whether something simpler existed, and described re-entering an
article with an instruction. That dissolves the hard part: each focused pass is
its own `raw_items` row, so it gets its own extraction and its own
`master_list` row through the **unchanged** accept path. No constraint dropped.
Two additive columns.

I had accepted the backlog's stated framing ("needs a schema change") and
designed to it rather than questioning it. **Third time today** — see the `$`
regex and the Cloudflare token.

## What shipped

`raw_items.split_instruction` + `split_parent_id` (migration `460b4ce`, applied
clean: 14,759 rows, all reading as unsplit originals). Then `b254f62`,
`fae3e20`, `02ae4a1`.

`POST /split/{item_id}` takes one focus line per deal. Line 1 re-focuses the
ORIGINAL row in place; later lines each clone the row and its article text.
Clones get `status='scraped'` so the title screener and scraper skip them, and
numbering continues past existing passes so re-splitting cannot collide.

## Two things that would have broken it

**The accept-time auto-reject scan.** It rejects same-company articles within
±7 days — and split passes share a company AND a publication date by
construction. Accepting deal 1 would have immediately auto-rejected deal 2 as
"already accepted from another source", and rejection has no undo. The feature
would have silently failed in exactly its canonical case. Found by reading the
scan's filter while stress-testing the plan, not by testing.

**Dedup.** `amounts_match(None, None)` is True, so two siblings with no stated
figure would flag each other and both vanish into Possible Duplicates. Fixed
with a `group_key` derived from `split_group_id` — deliberately NOT by changing
`amounts_match`, since two sources covering one undisclosed round is a real
duplicate worth catching.

## Deviation from the approved plan

Re-extraction runs **synchronously**, not as a `BackgroundTask`. Commit
`3fc8917` established that two callers on the single libsql connection is
unsafe, and FastAPI runs background tasks in a threadpool concurrently with
later requests — exactly that pattern. Synchronous adds no concurrency; the
cost is a few seconds' wait per deal.

## Self-inflicted, caught and fixed

A bulk edit silently converted CRLF→LF in three templates, rewriting 458 lines
of one. `pathlib.read_text()` normalises line endings in memory and writes them
back as LF. Restored and re-applied in bytes. Worth remembering before the next
bulk edit.

## Verified

Baseline and after, both **683 deals** — `export.yml` and `find_duplicates.py`
run against production via `migrate.yml`. Dedup guard proven inert on today's
data (no splits exist, so no two entries share a group key), siblings
suppressed, real cross-article duplicates still caught. Auto-reject regression
test passes all four cases. Split logic tested against a real DB including
re-split. Rendered triage page asserted free of the `#split-` marker.

## Not yet verified — needs Sam

The end-to-end split on a real roundup. `/split` is behind basic auth, so I
cannot exercise it. Watch for: two cards, separate amounts, no duplicate flag,
and the capital total rising by exactly the newly-captured figure.
