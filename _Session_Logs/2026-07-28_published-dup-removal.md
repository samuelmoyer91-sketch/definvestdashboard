# 2026-07-28 — Removing duplicates from the published list

Sam asked how the published dup check works and why it's so hard to delete the
duplicates it finds.

## What we found

It wasn't hard, it was **impossible**. Three separate gaps:

1. `/duplicates` was explicitly read-only — its own docstring said so.
2. The only action per row was an *Edit* link to `GET /edit/{id}`, which does
   nothing but `RedirectResponse("/master")`. No anchor, no filter. You clicked
   Edit on a specific duplicate and landed at the top of a 480-row list.
3. **No delete route for a published deal existed anywhere in the codebase.**
   Every `session.delete()` in `src/` targets investors or rejected items.

Scale on the local replica: 480 deals → 11 likely-dup clusters → 23 flagged
deals (~5%), **$545.5M** estimated double-counted. Worst cluster is Karman
Space & Defense (3 cards, 3 matching pairs).

## What was built (commit `410bb9e`)

- **Remove button on every row** of `/duplicates`, posting to
  `/master/{id}/remove`. Returns 204 to the AJAX caller and strikes the row out
  client-side — no reload, because a reload re-clusters the whole report and
  loses your place.
- **Soft delete, not hard.** New `removed_at` / `removed_reason` columns.
- **`/removed` page** with Restore, plus a nav link.
- **`active_master(session)` helper** — every user-facing read of the master
  list now filters `removed_at IS NULL`: master list, map, stats, sectors,
  investors, the dup report, the CSV / HTML / map-data exports, Telegram count.
- **Best-source ranking on the report.** Each cluster is now sorted with the
  existing `_source_sort_key` and the top row gets a green check. That logic
  already existed for the triage dedup UI and was simply never applied here, so
  the page now says which one to *keep*, not just which are duplicates.

## Key decisions

**Soft delete over hard delete.** Dedup is a heuristic — same company, ±5%
amount, 30-day window — so it will occasionally flag two genuinely separate
raises. An unrecoverable delete on a false positive is the failure mode worth
engineering against. Nothing is ever hard-deleted from `master_list`.

**Lookups by `item_id` deliberately do NOT filter on `removed_at`.** Only
user-facing *reads* filter. The accept path must still see removed rows, or
re-accepting an item would insert a second copy instead of updating the
existing one. This is commented at both `active_master()` and the model.

**`master_list.published` is vestigial** — 0 for all 480 rows, and the exporter
never reads it. It was tempting to reuse as a soft-delete flag; left alone,
because a column named `published` meaning "not deleted" is a trap. Worth
cleaning up separately.

## Verification

Ran the app against a copy of the replica that lacked the new columns, so the
startup migration was exercised too. Confirmed: migration applies cleanly;
remove returns 204; the row survives in the DB with `removed_at` set;
disappears from all nine pages and all three exports; re-remove is idempotent;
bogus id 404s; restore puts it back everywhere. Clicked through in a browser —
strike-through renders, Restore works, no console errors.

**Gotcha hit along the way:** `src/notifications/telegram_bot.py` is CRLF. A
one-line patch written via a Python `open().write()` silently rewrote all 333
lines to LF. Reverted and re-patched in binary mode. **Check line endings
before scripting an edit** — `models.py` is CRLF too; the Edit tool preserves
them, a naive Python rewrite does not.

## Production incident: the startup migration lied

Shipping this broke the triage app. Every page calling `active_master()` 500'd
with `no such column: master_list.removed_at`.

**Cause: DDL issued through the libsql embedded replica does not reach the
Turso primary.** The startup migration in `app.py` ran, logged
`"removed_at column added successfully"`, and the column was not there. This
was confirmed, not guessed — the repair job read the primary and reported both
columns `MISSING` before adding them.

**Fix: run DDL from GitHub Actions.** Actions writes to this database every day
and is the proven path. Added `scripts/migrate_soft_delete.py` (idempotent,
`--check` dry-run, verifies the columns are queryable after `sync_turso()`) and
a manual `.github/workflows/migrate.yml`. Ran it, and the app recovered.

```bash
gh workflow run migrate.yml -f script=<name>.py
```

The in-app block was hardened rather than removed: `PRAGMA table_info` instead
of try-SELECT-except-ALTER, plus a verification pass that logs a loud
`SCHEMA:` error naming the fix. It no longer claims success it cannot confirm.

**Two process failures worth remembering:**

1. **A local SQLite pass is not evidence for Turso.** The migration was tested
   against plain SQLite, where it works perfectly. Different write path.
2. **`/health` does not exercise the database.** It returned 200 for the entire
   outage, and polling it was reported as evidence the deploy was clean. Any
   future schema change needs a check against a page that actually reads
   `master_list` — and those are all behind basic auth, so that check belongs
   to Sam, before the work is called done.

## Correction to the numbers above

The migration reported **628 active deals** in production. The duplicate
analysis in this log (480 scanned, 23 flagged, $545.5M double-counted) came
from the local `turso_replica.db`, which is stale. **The real figures are
higher.** Cluster counts and the overcount estimate on the live page will not
match what is written above.

## Open

- The dedup blind spot Sam should know about: `amounts_match` returns False
  when one side has an amount and the other doesn't
  (`src/utils/dedup.py:194`). So "Anduril raises $250M" vs. a local write-up
  with no figure is **never** flagged. Fixing it means matching on company +
  tight date window when only one side has a figure — more false positives,
  which is now survivable since removal is reversible. Not done.
- A real merge (combine two records, keep the better source) — not done;
  Remove + keep-the-check-marked-one covers the practical case.
- Unchanged: `\b\$\b` regex bug, deal-splitting needs a schema change,
  country-centroid pin stacking, `published` column cleanup.
