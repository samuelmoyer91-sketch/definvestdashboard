# 2026-07-29 — Accept latency: fixing the measurement, not yet the bug

Accept clicks take 10–15s in production. **Not solved.** What changed is that
it can now be measured; two attempts to fix it by reasoning both failed.

## The mistake worth remembering

I guessed twice and shipped both guesses.

1. **Browser DOM cost** → paginated to 20 cards. Helped, not the cause.
2. **Per-click `sync_turso()`** → moved to a dirty flag (`mark_dirty()`),
   syncing on the next page render instead. Sam: "roughly the same."

Then I built instrumentation that *also* could not see the problem, and only
found out because Sam pushed back:

> "I suspect your diagnostics are somehow missing that, which might undermine
> your ability to actually solve the problem."

He was right. `_Phases()` started on the **first line of the handler body**, so
it would have reported ~76ms whether the click took 76ms or 15 seconds.
Invisible to it:

- **`Depends(get_db)` → `get_session()`** — connection acquisition. `StaticPool`
  keeps ONE connection per process, so a request blocks here whenever anything
  else holds it. This runs *before* the handler body.
- **`BasicAuthMiddleware`**, and reading/parsing the form body.
- **Event-loop queueing.** Every route is `async def` doing blocking SQLAlchemy
  I/O, so one slow request stalls the loop for every other.

## What now exists (commit `79f9bb6`, live in production)

A pure-ASGI `RequestTimingMiddleware` wrapping the whole call — pure ASGI
rather than `BaseHTTPMiddleware`, which adds its own per-request overhead and
would pollute the measurement. It reports:

| Field | Meaning |
|---|---|
| `total_ms` | whole request, inside the app |
| `pre_handler_ms` | **the gap the old timers could not see** |
| `session_ms` | `get_session()` alone |
| `phases` | the old per-phase handler breakdown |

**`pre_handler_ms` is the number that matters.** Large pre-handler with a small
`handler_total` means the app is *waiting*, not *working* — a different bug
from a slow query, needing a different fix.

Verified it detects what the old version missed: one accept in isolation gives
total 75.6ms / pre-handler 3.7ms; eight fired concurrently push median
pre-handler to **66.9ms** with handler work unchanged.

Readable without auth at `/health` (also `/api/diagnostics`, and a
`Server-Timing` header reading `prehandler / session / <phases> / handler`).

## Also fixed: I could not verify my own deploys

`/health` returned 200 throughout the schema outage while every real page
500'd, and I reported the deploy clean on that basis. It now reports the
running commit sha, uptime, `last_sync_ms` and `pending_sync`. Confirmed
working in production — `commit: 79f9bb65`.

`last_sync_ms: 149.1` on production, incidentally: a Turso sync is ~150ms, not
seconds, which further weakens the sync hypothesis.

## Tomorrow

Nothing to set up. The instrumentation is live; the next real triage session
records everything. Read it with:

```bash
curl -s https://capitalfordefense.up.railway.app/health | python3 -m json.tool
```

Then interpret:

- **pre_handler large** → blocked. Prime suspect is the single `StaticPool`
  connection plus `async def` routes doing blocking I/O.
- **handler_total large** → the work itself; `autoreject_scan` is the biggest
  phase at ~54ms locally.
- **both small** → the time is outside the app: Railway proxy, network, or
  browser.

A seeding tool (`scripts/seed_timing_test.py`, commit `81e2c46`) exists for
measuring against a queue that is empty — it creates clearly-marked disposable
items and cleans up completely, verified to return the DB to its exact
baseline. Not needed while real items are arriving.

## Open

- The actual cause of the 10–15s. Unknown; now measurable.
- `normalize_company()` prefix gap in `dedup.py` (see the drone/EW log).
- Euro conversion producing Exail's `$3.9B`.
