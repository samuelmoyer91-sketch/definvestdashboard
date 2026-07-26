# Session Log — 2026-07-26
## Europe on the map, and the discovery that Google News feeds have been dead since March

Two things shipped, and one significant thing was discovered by accident.

---

## 1. Europe map (shipped, live)

**Premise correction.** The starting idea was "we already catch European deals, just add a map toggle."
Half right: the deals were there, but **every non-US deal had NULL coordinates**, because
`scripts/geocode_locations.py` skipped anything non-US by design — `parse_location()` returned None
unless the string ended in a US state, and the Nominatim call hardcoded `", USA"` + `countrycodes='us'`.
A toggle alone would have rendered an empty Europe. The geocoder was the actual work.

**Geocoder** (commit `4a455b8`) — added an international branch: geocode globally, skip the TIGERweb
lookup (congressional district is US-only, so those rows keep a NULL district; the map popup already
guards for it). Guards added for real data messiness:
- placeholder values (`Unknown`, `Multiple European Countries`) skipped rather than geocoded into nonsense
- bare `Georgia` → the country, not the US state. Needed BOTH a parser guard and a structured
  `country=` Nominatim lookup, because Nominatim itself also prefers the US state.
- misspelled trailing country (`Yateley, Hampshire, United Kingdon`) retries without the last part
- **pre-existing US bug fixed**: the strip-USA regex missed a bare `US` suffix, so `Rockford, IL, US`
  — a US deal — was being skipped entirely

Verified against every location string in the DB: **0 of 222 US strings changed**, 100 international
locations became geocodable.

**Map region control** (commit `3ee559f`) — US / Europe / All selector on `github_site/deals/map.html`.
Viewport-only by choice: it moves the camera, never filters pins, so the deal count stays honest.

**Live result:** 173 international deals geocoded, **107 European-theater pins** where there were zero.
Of 188 non-US rows: 173 geocoded, 13 correctly skipped as placeholders, 2 failed.

### Rabbit hole worth remembering (cost ~50k tokens)
Europe framing was wrong at first (view ballooned to half the globe, Washington DC visible in "Europe").
Correct diagnosis — Leaflet snaps to integer zoom, so fitting a Europe-shaped box into a wide container
rounds down. **Wrong fix**: `zoomSnap: 0` (fractional zoom), which collides with leaflet.markercluster.
Then chased a phantom: "markers scattered outside the container" — which also happens in the *unmodified*
US view, because Leaflet legitimately keeps off-screen pins positioned off-screen. Was measuring with the
wrong instrument, in a preview pane that kept collapsing to zero width.
**The fix was 4 lines**: drop `zoomSnap`, use `setView([48,15], 4)` for Europe. Lesson: for visual bugs,
verify visually; and suspect your own most recent change before suspecting the library.

---

## 2. THE BIG FINDING: Google News feeds have been dead since March

Surfaced while verifying an unrelated change. A manual ingest run showed **74 items passed AI screening
and 0 could be scraped**.

**Cause:** Google News RSS links (`news.google.com/rss/articles/...`) now return an **11-character
JavaScript stub with no meta-refresh tag**. The scraper's redirect handling looks for
`<meta http-equiv="refresh">`, which is no longer there, so there is no path to the article.

**Critical distinction — the two Google feed types behave differently:**
| Type | URL shape | Status |
|---|---|---|
| Google **News** | `news.google.com/rss/search?...` | ❌ dead — 11-char JS stub, no recovery |
| Google **Alerts** | `google.com/alerts/feeds/...` | ✅ still works — page carries meta-refresh the scraper follows |
| Direct publisher | e.g. `spacenews.com/feed/` | ✅ 5,000–7,000 chars, 98–100% success |

**Measured from the deal history (not assumed):**
```
scrape success   Jan 73% | Feb 71% | Mar 0% | Apr 0% | May 0% | Jun 0% | Jul 0%
deals produced   Jan 6 | Feb 15 | Mar 3 | Apr 3 | May 0 | Jun 0 | Jul 0
```
All-time Google News produced only **27 of 480 deals (6%)**.

**Why it didn't hurt:** the direct-feed migration in late May/June replaced the capability almost exactly
as it died. June was the **best month on record (133 deals)** with Google News already at zero.

**Actions:** commits `2f6414a` and `a52cd58` disabled all 9 Google News feeds (3 that had just been
enabled that morning, plus the 6 pre-existing). Feeds went **15 → 9**: 7 direct + 2 Alerts.

---

## 3. Kept from the aborted Europe Phase 2 (commit `2f6414a`)

The European *feeds* drafted for Phase 2 were Google News and would have been equally unscrapable, so
they were dropped. The classification work was kept — it still helps European deals arriving via direct feeds:

- **Scorer vocab**: added `defense` and `defence`. **Neither was a keyword at all** — only the compounds
  "defense contractor"/"defense tech" — so `Lockheed Martin Ventures to invest $100M in European defense
  firms` scored **0.00** and auto-rejected. Also added `nato`, `bundeswehr`, plus the debt/minerals
  vocabulary (`venture debt`, `private credit`, `rare earth`, `critical minerals`, …).
- **Title screener**: states European/allied deals are fully in scope (all its exemplars were US firms);
  European outlets added to the trusted-source list.
- **Summarizer**: EDF / EDIRPA / EDIP / ASAP, NATO Innovation Fund, UK NSSIF and national MoD capacity
  awards now classify as "Government Support" instead of defaulting to "Contract/Award".

---

## Open threads / where to pick up

**The strategic risk, and the most valuable next move:**
**82% of all deals come from just two Google Alerts feeds** (New Factory 192, Private Equity Defense 172).
Those are also Google-operated and survive only because their redirect still carries a meta-refresh — the
exact thing Google removed from News. If that goes, four-fifths of deal flow disappears overnight.
→ **Broaden direct publisher coverage**, with European outlets included. This de-risks the Alerts
dependency *and* serves the Europe request in one move. Candidates to evaluate: Sifted, Janes,
Euro Security & Defence, Defense News Europe, Politico Europe Defence, plus more US direct sources.

**Also open:**
- Europe Phase 2 proper — must use **direct European publisher RSS**, not Google News.
- The `$` deal-indicator only matches when glued to a preceding character (`US$1.8bn` matches,
  ` $100M` does not) because the pattern is `\b\$\b`. Untouched — affects every feed, own decision.
- Deal-splitting for multi-deal articles (one source → several cards). Needs a live schema change
  (unique constraint on `master_list.item_id`). Explicitly deferred, wants its own session.
- Scrape failures on *direct* feeds (~5 of 18 on a normal day) — worth a time-boxed look.
- Country-only locations (`"UK"`, `"France"`) geocode to a country centroid, so several deals stack on
  one point. Fix would be upstream in the summarizer prompt, not the geocoder.
- Map: State/District dropdowns are US-congressional-district-based and stay US-only. If Europe becomes
  a first-class view rather than a camera position, it would want a country filter.

**Health at session end:** pipeline green for 13 consecutive days before today; both of today's runs
succeeded. 9 feeds enabled (7 direct + 2 Alerts). Next scheduled ingest 11:00 UTC — first run on the
slimmed feed list, worth a glance.
