# 2026-08-12 — Turso outage, sync burn, and the refusal answer

Sam reported failure emails. Both pipelines were down. Nothing was wrong with
the project; two genuinely useful things fell out of investigating it anyway.

## The outage — Turso's, and it cleared itself

Publish failed 03:17 UTC, ingest 11:36 UTC, both in under a minute:

```
Turso connection failed: Hrana: api error: status=502 Bad Gateway,
body={"error":"upstream forward failed"}
```

No code had changed — `ee8293e` was still the tip and had run fine on 08-10 and
08-11. A live probe at ~12:50 UTC still 502'd, so it was ongoing, not a blip.

**Two hypotheses, both wrong, both killed by data rather than argument:**

1. *Quota exhaustion.* `turso plan show` — nothing above 58%, overages enabled.
2. *A dependency change* (nothing is pinned; `pip install` resolves fresh every
   run). Identical libsql versions on the last working and first failing run.

What settled it: `turso db shell` queried the same database fine while our code
could not connect. Queries and embedded-replica sync hit **different Turso
endpoints**, and only sync was broken. `turso group list` reported Healthy,
`db show` showed nothing archived, and Turso's status page showed all-clear
throughout — so it never appeared as an incident.

It cleared on its own. `scripts/probe_turso_modes.py` (written during this)
confirmed all three connection modes working again.

Caught up afterwards: ingest 184 new items / 49 summaries, export 711 deals
(683 → 711, so Sam's weekend triage is in), publish succeeded and the public
site is no longer frozen at 08-11.

**Note for next time:** capitalfordefense.com was never affected. Cloudflare
serves static files, so a database outage leaves it stale, not down.

## The real find: 5.8 GB of embedded sync

`turso db inspect` showed **5.8 GB of embedded syncs against a 10 GB limit**,
for a 176 MB database.

Cause: `get_engine()` builds a libsql *embedded replica* whenever the Turso env
vars are set. Every GitHub Actions run gets a fresh container, so the replica
has nothing cached and **downloads the entire database to run one script and
exit**. Ingest, publish, every export, every diagnostic.

At roughly 350 MB/day that was ~12 days of headroom, and overages are enabled,
so it would have arrived as a bill rather than a failure.

Fixed in `1035da5`: `TURSO_REMOTE_ONLY=1` on every workflow step carrying the
Turso credentials makes one-shot processes connect straight to the primary — the
way `turso db shell` does — and `sync_turso()` becomes a no-op because writes
already landed there. Verified against production via `export.yml` (711 deals).

The Railway app deliberately keeps its replica: it is long-lived, so the replica
persists across requests and syncs incrementally.

⚠️ **Worth confirming**: `turso db inspect defense-tracker` should still read
~5.8 GB. A silent fallback to replica mode would look identical to success.

## The refusal answer — and why no fallback fixes it

The `stop_details.category` logging added on 08-08 finally paid off:

```
stop_reason=refusal, category=bio
explanation=API integrators: you can reduce refusals ... configuring a fallback model
```

**`category=bio`** — the biology classifier, not the paywall theory. 6 failures
in today's ingest on top of the 9 long-standing ones.

Anthropic's message names a fix, so it was tested against an article that is
actually failing (item 12881). It does not work:

| Approach | Result |
|---|---|
| Server-side `fallbacks` parameter | **400** — `'claude-sonnet-5' does not support the fallbacks parameter`; `allowed_fallback_models = []` |
| Retry on `claude-sonnet-4-6` | refuses, `category=bio` |
| Retry on `claude-opus-4-8` | refuses, `category=bio` |
| Retry on `claude-haiku-4-5` | answers — with *"Unfortunately, I cannot extract…"* |

Every model declines the same content, so a client-side fallback would refuse
three times and cost more. **Decision: build none.**

**The better lead, unresolved.** The test article is *"AI, dual use and
spacetech: the new stars of debt funding"* — a European VC funding roundup,
which has no business tripping a *biology* classifier. That points at the
scraped text not being the article. Sifted is paywalled, which would also
explain why it is always the same articles.

`scripts/inspect_failing_text.py` exists to answer this and runs clean, but its
output could not be retrieved through the Actions log API — read it in the
GitHub web UI instead. If the text is paywall boilerplate this is a **scraper**
problem, not a model one.

## Process notes

- Blocked on a 10-minute `gh run watch` and made Sam wait. Background long runs
  from the start.
- Burned several turns on Actions log-retrieval mechanics rather than the
  question. When `gh run view --log` will not surface a script's output, read it
  in the web UI instead of escalating to log-archive downloads.
- Three of the day's four hypotheses were wrong (quota, dependencies, paywall).
  Each was cheap to kill because it was checked rather than argued.

## State at close

Working tree clean, everything pushed (`a82aa15`). Pipelines healthy and caught
up. Backlog tidied: item 6 de-duplicated, the shipped roundup item moved to
DONE, and item 5's "embedded replica for reads" suggestion corrected — the app
already runs one, which is why that would have been a dead end.
