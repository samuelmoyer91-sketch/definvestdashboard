# Session Log — 2026-06-06 to 2026-06-09
## Feed verification, segment gap-fill, conference target list, currency conversion

Continues the direct-RSS feed work from 2026-05-31. Spans a few sittings.

## 1. Direct-feed migration VERIFIED complete (6/6)

Built `scripts/verify_feeds.py` (read-only, reusable) and ran it against live Turso (Sam pasted creds into a gitignored `.env`, deleted after). Results:
- **Gate PASSED:** direct feeds scrape **90% clean @ 5,800 avg chars** vs Google **55% @ 3,801**. The Google-redirect/empty-stub premise is confirmed solved for direct sources.
- **Payoff confirmed:** 5 published deals from direct feeds in ~6 days (SpaceNews ×2, PR Newswire ×2, Defense News ×1).
- Newswire feeds ~85% auto-reject (noisy source, filter handles it); trade-press ~65-70% pass. Dup load trivial.

**Actions taken (commit `eb08fa4`):** enabled `Direct: Pulse 2.0` (final direct feed); retired `Carlyle Defense` + `Defense Corporate Ventures` (0% lifetime accept). Net 13 feeds at that point.

`.env` was DELETED after the verify run (Sam's call — token off disk).

## 2. Segment gap-fill feeds (6/6, commit `351e4d5`)

Gap analysis across 4 axes (instrument / investor type / geography / sub-sector): strong on instrument+US-sector, weak on investor breadth + capital type. **Sam deprioritized international** (happy to have, not comprehensive). Chose to fill the rest. Design principle reaffirmed: transaction-signal > named-entity feeds.

5 new feeds added (all verified to return items + headlines sampled before enabling):
- **LIVE:** `Generalist Defense Investors` (megafund/crossover-led rounds — Founders Fund, Thrive, General Catalyst, 8VC, Sequoia, Lux, Coatue), `Gov Strategic Capital` (OSC/STRATFI/TACFI).
  - **Lesson:** first Gov Strategic Capital draft used "Defense Production Act"/"Title III" → returned ~all Trump/coal/energy noise. Tightened to defense-specific program names + capital verb. Now clean.
- **STAGED OFF** (need scorer-vocab added first, or low-volume): `Defense Private Credit`, `Defense Critical Minerals`, `Defense Corporate Ventures v2`.
  - Credit + Minerals: the keyword scorer lacks debt/minerals vocabulary, so enabling without adding multi-word phrases ('venture debt','private credit','rare earth','critical minerals') would auto-reject their items at stage 1. Add those phrases in the SAME commit that flips them on. Corp VC v2 uses existing vocab, can enable anytime.

## 3. Conference target-list spreadsheet (one-off deliverable)

Built `Conference_Target_List v.1.1.xlsx` (project root; v.1.0 archived to `_Archive/`). NOT committed to git (output artifact). Three tabs:
- **Target Companies** (291) — A: company, B: capital raised (clean USD number, summed per company), C: location (US state / country), D: technology area (sector tags). One row per company, sorted by capital, filters + frozen header.
- **Investors** (492) — every investor in the tracker, ranked by deal count (Sam's addition).
- **Notes & Methodology** — documents all judgment calls.

Key decisions: excluded VC/PE funds raising their own LP funds (N.S. Lachman, Veritas, Greenbriar, McNally, Carlyle, a16z) from the Target tab — they're investors, moved to Investors tab. Multi-deal companies: capital summed, tags merged. A few tracker artifacts flagged for manual eyeball ("Multiple (...)" rows, Unknown locations).

## 4. Currency conversion (6/9) — IMPORTANT scope correction

Sam asked to smooth currency handling. Initial fix went into `dedup.parse_amount` (spreadsheet/dedup only). Sam clarified he meant **the actual website**. Investigation found the codebase had **THREE separate amount parsers**, none currency-aware:
1. `dedup.parse_amount` (dedup, verify, spreadsheet)
2. `app.py:_parse_amount` (triage /sectors aggregation)
3. public site rendered raw strings (no parser, no totals)

Decisions: **convert to clean USD, no dual-currency display** (for simplicity + queryability); **fix all parsers**.

Changes:
- `src/utils/dedup.py` (commit `5426f0c`) — added `FX_RATES` table (EUR 1.08, GBP 1.27, CAD 0.73, AUD 0.66, JPY, INR, ILS) + `detect_currency()`; `parse_amount` now converts non-USD → USD. Fixed rates by design (simple, stable, comparable over time). `parse_amount(convert=False)` preserves raw behavior.
- `src/export/export_to_html_v2.py` (commits `ae8b7f7`, `76f1c4b`) — public deal cards now show converted USD via `display_amount()` (e.g. €110M → $118.8M, clean, no parenthetical).
- `src/web/app.py` (commit `76f1c4b`) — `/sectors` `_parse_amount` now delegates to `dedup.parse_amount`.

**All three data-path parsers now route through `dedup.parse_amount` — one source of truth + FX table.** Remaining matches are display-only formatters and triage client-side JS input helpers (USD entry), intentionally left alone. Only 1 non-USD deal in current data (Smiths Detection £2B → $2.54B); matters more as international feeds grow.

Edge case left alone (per "simple, not perfect"): "crore" (Indian 10M) not handled; absent from data, fails safe.

## Pushed
All commits through `76f1c4b` are on `main`.

## OPEN — needs action to go live on public site
The public-site currency change is on `main` but **not yet published**. Public site does NOT auto-deploy. To make it live: `gh workflow run publish.yml` (or wait for 1 AM UTC cron). Sam was asked; pending his call.

## Next steps / still queued
- Trigger publish.yml to push currency conversion live (pending Sam).
- Enable the 3 staged gap-fill feeds (add scorer vocab for Credit + Minerals in same commit; Corp VC v2 anytime).
- Watch Pulse 2.0 + new live feeds for noise; re-run `verify_feeds.py` in ~a week.
- Lower-priority Phase 3: rewrite New Factory query, fix In-Q-Tel scorer, consider SEC EDGAR/SAM.gov.

---

# 2026-07-03 — Design review + stale-chart fix (PAUSED mid-work, token limit)

## Done & committed (NOT pushed — Sam to approve)
- `db56a6c` — **Real find: indicators charts stale since 2026-02-13.** VC/M&A charts: openpyxl missing from requirements.txt → private_capital_fetcher failed daily in CI. ITA/XLI/PLD: yfinance 0.2.37 broken vs Yahoo → bumped to 1.0 (verified locally end-to-end). Root enabler fixed: generate_site.py now writes step_failures.log; publish.yml fails AFTER deploy → issue notification. Also committed locally-refreshed data JSONs.
  - NOTE: map + FRED timestamps were FALSE alarms (my local mirror served stale repo JSONs; live is fresh). vc/ma/ita/xli/pld staleness was REAL.
- `b46b7d0` — Homepage nav brand (unhid .logo slot), subtitle text-wrap:balance, About grid-2→grid-4, map marker clustering (leaflet.markercluster, brand-green bubbles). Clustering NOT browser-verified yet.

## REMAINING from the approved design-review list
1. **Deal card redesign** (export_to_html_v2.py) — amount as visual hero (big, top-right), metadata 2×2 grid instead of stacked lines (~40% height cut), sector chips, green left-edge accent. Plan: implement + render mock with fake data (no DB needed — call generate_deal_card with mock objects), screenshot before/after for Sam, then ship.
2. **Deals-page nav is missing "Deal Map" link** (export_to_html_v2.py ~line 220, insert `<li><a href="map.html">Deal Map</a></li>`) + trim "Read Full Article" domain to root (extract_domain fn).
3. **Chart styling** (generate_chart_pages_v2.py ~line 485): x-axis year labels repeat ("2020 2020 2021…") — add ticks callback suppressing consecutive duplicate labels + maxRotation 0; lighten gridlines/plot bg.
4. After push: trigger `gh workflow run publish.yml`, verify live (clusters on map, nav brand, fresh VC/M&A + ETF chart data), and confirm next daily publish goes green with no step_failures.
