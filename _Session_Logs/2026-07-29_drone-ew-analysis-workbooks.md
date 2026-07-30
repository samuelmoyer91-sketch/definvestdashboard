# 2026-07-29 — Drone & EW analysis workbooks

Sam asked for a spreadsheet of every drone and EW deal with investors and
company names, for a research project. Then a second, investor-centric cut.

## Deliverables

- `Drone_EW_Deals v.1.0.xlsx` — 167 deals, one row each. Deals tab +
  Summary tab with live formulas.
- `Drone_EW_Investors v.1.0.xlsx` — 386 rows, one per investor per deal,
  333 third-party investors across 115 companies. Investors tab + Investor
  League tab.

Both left untracked in git, matching how other workbooks in this project are
handled (`Conference_Target_List v.1.1.xlsx` is untracked too).

## Getting the data was the real work

Three possible sources, and the obvious two were both wrong:

| Source | Deals | Company name |
|---|---|---|
| Local `turso_replica.db` | 129 | 98% — but 3 weeks stale |
| Scraping capitalfordefense.com | 166 | **72%** |
| **Production export via Actions** | 167 | **99%** |

The replica was stale by 37 drone/EW deals — and Sam asked for *recent* work,
so the staleness hit exactly the rows that mattered most. The public site has
everything current, but `export_to_html_v2.py` renders
`heading = title_display or company_name`, so the **headline replaces the
company name** and 46 rows would have come through blank.

Built `scripts/export_deals.py` + `.github/workflows/export.yml` (commit
`e6b9fb4`) — CSV export with an optional sector filter, run from Actions where
the Turso credentials live, uploaded as an artifact. Reusable:

```bash
gh workflow run export.yml -f sectors="Autonomous Systems/Drones,Electronic Warfare"
```

## Data-quality findings worth acting on

**1. Confirmed double-count — Thales/Exail, 2026-07-08.** The same acquisition
is in twice: `$4.5B` and `€3.9B`. The euro figure was stored as
`$3,900,000,000` — converted 1:1 rather than at rate. Two compounding bugs:
the currency conversion failed, *and* that failure pushed the two amounts 15%
apart, outside the dedup's 5% tolerance, so the duplicate checker never saw
it. Overstates the drone/EW total by ~$3.9B.

**2. `normalize_company()` does not strip descriptive suffixes.** It handles
legal ones (`inc`, `corp`, `ltd`, `holdings`, `group` are in `NAME_NOISE`) but
not words like "Industries" or "Technologies". So these never get compared:

- `Anduril` vs `Anduril Industries`
- `Katalyst Space` vs `Katalyst Space Technologies` — both $12M, 5 days apart,
  near-certainly one round reported twice
- `AeroVironment` vs `AeroVironment, Inc.` (this one *does* normalise)

Prefix matching on the normalised name catches all of them and does **not**
wrongly merge `General Dynamics` / `General Atomics`, which a first-word match
would. That is what the workbooks' Review column uses. **This is a real gap in
`src/utils/dedup.py` affecting both the triage and published dup checks** —
not fixed, Sam's call.

**3. Amount parsing.** `$11M` shorthand sits alongside `$11,000,000` in the
same column, and `Unknown` appears as a literal. Handled in the workbook
builder; the app's own parser may or may not cope.

**4. Investor-string fragments.** `parse_investors()` splits on commas, so
"AeroVironment, Inc." yields a bare `Inc.` as its own investor (5 rows).
Dropped bare legal suffixes when building. Also merged "the NATO Innovation
Fund" with "NATO Innovation Fund".

## Analytical cautions recorded in both workbooks

- Only **62 of 167** deals are external investment. The rest are internal
  corporate programs, M&A and government awards — so the headline "$57.7B in
  drone/EW" is misleading; external-investment-only is **$21.7B**.
- **Never sum the Amount column on the investors sheet.** It repeats whole
  deal size on every investor row, so a five-investor round counts fivefold.
  The data has no per-investor allocations.
- Government bodies (JobsOhio, DGA, CNES, European Commission) are third
  parties but not equity investors.
- JobsOhio shows 4 deals but is really 2 events — both Review-flagged pairs.

## Verification

No LibreOffice on this machine, so `recalc.py` could not run and formulas were
**not** executed. Verified instead by: checking every formula range against the
real data extent (all `2:168` / `2:387`), confirming each referenced column
letter matches its intended header, restricting to Excel-2007-era functions
(`COUNTIF`, `COUNTIFS`, `SUMIF`, `SUM`, `MEDIAN`, `MAX`, `COUNTA` — no
`XLOOKUP`/`FILTER`/`TEXTJOIN`), and computing every summary figure
independently in pandas. Formulas will evaluate on open; they have not been
seen to evaluate.

## Open

- Fix the `normalize_company()` prefix gap in `dedup.py` (finding 2).
- Investigate the euro conversion that produced Exail's `$3.9B` (finding 1).
- Remove the Exail duplicate via the new Remove button on /duplicates.
