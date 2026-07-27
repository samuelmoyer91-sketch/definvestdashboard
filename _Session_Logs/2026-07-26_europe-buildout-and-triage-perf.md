# Session Log — 2026-07-26 (part 2)
## Europe build-out, feed-health monitoring, and two production fixes

Continues `2026-07-26_europe-map-and-dead-google-feeds.md` (same day, earlier session:
Europe map shipped, Google News feeds found dead since March).

Commits: `be0a536`, `2fed0d8`, `cd317ff`, `8f7dfa8`, `785d68d`, `b6bb7c2` — all pushed.

---

## 1. Europe made browsable (shipped, live)

Sam picked "a solid, browsable Europe section" — US stays the centre of gravity, but Europe
is properly navigable — over co-equal-region or analytics-led options.

**Region filter on the deals page (`2fed0d8`).** The conspicuous gap: the deals page filtered
by sector and capital type only, with **no geography anywhere**. A user told the dashboard covers
Europe could see 107 map pins and still not produce a list of European deals. Added a region
dropdown where regions are selectable directly with countries nested beneath — "All Europe (95)"
or "Germany (20)", one click either way. Cards carry `data-region`/`data-country` from a new
`location_region()` helper in `export_to_html_v2.py`.

Taxonomy is deliberately coarse and gives the US its own top-level region rather than burying it
in North America (~85% of the dataset). **NOTE: this is a taxonomy and deliberately differs from
the map's Europe view, which is a viewport box and so also frames Israel and Turkey.** Flagged to
Sam; he was fine with it.

- **Bug caught in testing:** treating any two uppercase letters as a US state abbreviation filed
  `"London, UK"` under the United States, hiding all UK deals from Europe. Now matched against an
  explicit state list. Would have looked fine at a glance and been quietly wrong.
- Verified on all 434 located deals: 421 classified, 13 correctly left unclassified as placeholders.
  In-browser: Europe/Germany/Middle East/Canada each return only matching cards, zero false
  positives; Ukraine (3 deals, below page size) shows exactly 3. Four controls still fit one row
  on desktop, stack cleanly on mobile.

**Live after publish:** US 374 | **Europe 95** | Asia-Pacific 34 | Other 30 | Middle East 14.
European leaders: UK 23, Germany 20, France 10, Italy 5, Poland 4, Ukraine 4, Netherlands 4.

## 2. European feeds (two rounds)

**English-language (`be0a536`).** Added Defence Industry Europe, Euro Security & Defence, Sifted.
Rejected after testing: Tech.eu / EU-Startups (general tech noise), Naval News / Defence Blog
(war reporting, not capital events), European Defence Agency (no working RSS).

**Local-language (`8f7dfa8`).** Sam's insight, and he was right: *direct feeds don't replace
breadth.* The US long tail comes from **Google Alerts — a search across the whole web** — which is
why 2 Alerts feeds produce 82% of deals while 10 direct feeds produce the rest. Adding N European
publishers gives N publishers, not a European long tail. I'd conflated "replaced the reliability"
with "replaced the reach" in the earlier session; corrected.

Added ESUT (DE), Augen geradeaus (DE), Opex360 (FR), Portail de l'IE (FR) — all verified to return
items and scrape full text first.

**New capability: `skip_relevance_filter`** (per-feed flag in `config/feeds.json`, read in
`rss_fetcher.py`). The keyword scorer matches English word stems, so German/French headlines score
~0.00 and auto-reject at stage 1 before the AI sees them — same failure mode as the missing
`defense` keyword. For feeds whose own editorial focus already does the filtering (cf. In-Q-Tel's
"any mention is relevant"), skip the scorer. **Translation is NOT needed** — Sonnet 5 reads
German/French natively and still emits English summaries; only the stage-1 keyword gate is the
blocker. Items get `relevance_flags = "SKIPPED_FILTER:non-english-feed"` so this stays visible in
the data.

Verified end-to-end on a real headline (KNDS's €100M Görlitz tank-production expansion): scores
0.00 and auto-rejects on the normal path, correctly reaches `status='new'` under the bypass.
Production ingest confirmed all four fetch, and where scraped: ESUT 4/4, Opex360 6/6,
Portail de l'IE 1/1 (100%).

### Google Alerts for Europe — UNRESOLVED, Sam's action
Sam tried creating German/French Alerts; preview showed "no recent results" even for a bare
`Rüstungsindustrie`. I verified the same queries return 100 real items against Google News RSS,
so **content exists — it's Alerts specifically**. The feed URL he created is valid
(`.../alerts/feeds/09025431128020683164/15398985734618585888`, HTTP 200) but returns 0 entries.

Untested hypotheses, in order of likelihood — **check "Region" and "How many" first**:
1. **"How many" = "Only the best results"** (the UI default) rather than "All results" — known to
   be very sparse for new/non-English queries.
2. **Region** set to something other than "Any region", intersecting with Language=German → near-empty.
3. Alerts' matching index genuinely being thin for non-English (would be a real limitation, not a bug).
4. Curly quotes from autocorrect breaking the parser.

Diagnostic suggested: create an Alert with a plain English high-volume query (`Lockheed Martin`).
If that previews fine and German doesn't, it's language-specific. Also worth checking what settings
the two *working* Alerts feeds use.

**If Alerts URLs ever arrive: wire them in with `skip_relevance_filter: true` (same as the four above).**

## 3. Feed-health canary (`cd317ff`)

Direct response to Google News being dead 5 months unnoticed. `article_scraper.py` now tracks
attempted/succeeded per `feed_source` and writes `feed_health_alerts.log` when any feed with **>=5
attempts** scores **<30%**. `ingest.yml` checks it **after** summarization — so a degraded feed fails
the run and opens an issue naming the specific feed/rate, without blocking summarization of whatever
did scrape. Mirrors the existing `step_failures.log` pattern in `publish.yml`.

Threshold from 60 days of real history: Alerts feeds' worst single day (n>=5) was 43%; direct feeds
almost always >=90%. 30% leaves margin above normal variance while catching a collapse same-day.
Verified against real healthy-day numbers (43%, 50% — no false positive) and the actual March
collapse shape (0% at volume — alerts correctly), plus a real end-to-end run.

**Reframe worth keeping:** Sam pushed back on treating the 82% Alerts dependency as a strategic
threat. He was largely right — Alerts is 23 years old, survived Reader, and has been rock-steady at
77% while News went to 0%. The risk was never a *shutdown*: Google News RSS didn't shut down either,
its redirect page format changed. **The correct response is monitoring, not diversification** — the
real lesson from the March incident was detection, not concentration.

---

## 4. Two production fixes

### Turso stale-connection 500 (`785d68d`)
Triage threw `ValueError: Hrana: stream not found` on the first visit of the morning. **Not caused
by any of our changes.** Turso expires an idle Hrana stream server-side; the connection cached
overnight is dead by morning.

A liveness check for exactly this already existed — but **could never run**: `StaticPool` calls the
engine's creator once, and `get_engine()` returns the cached `_turso_engine` thereafter, so the
check inside the creator was dead code after startup. Write paths recovered anyway (scrapers catch,
reset, retry); the **read path had nothing**, so loading triage just failed.

Fix: probe in `get_session()`, but **only after an idle gap** — active use pays no extra round-trip,
while the first request after a quiet period transparently reconnects. Plus a backstop in the web
app's global exception handler: on a stream error, drop the cached connection so the next request
rebuilds it rather than every request failing until redeploy.

### Triage speed: ~10s per accept (`b6bb7c2`)
**Regression** — the 2026-02-18 session had taken this from 10s to <1s.

Measured rather than assumed. Server side was never the problem:
```
triage queue query (200 items, joinedload) : 0.067s
load all master_list rows for dedup        : 0.014s
dedup.find_queue_duplicates (the O(n^2))   : 0.003s   <- my first suspect; wrong
template render                            : 0.041s
```
The cost is **in the browser**. Accept/reject both 303-redirect to `/`, rebuilding the *entire*
queue every click — 200 cards, each a full form with ~40 inputs including 22 sector checkboxes:

| | before | after |
|---|---|---|
| HTML | 6.2 MB | 0.6 MB |
| gzipped (wire) | 535 KB | 53 KB |
| `<input>` elements | 8,010 | 810 |
| DOM nodes | 15,424 | 1,564 |

Fix: render the top `TRIAGE_PAGE_SIZE = 20` (one constant in `app.py`). Dedup still runs over the
full 200 so the Possible Duplicates split is unchanged; "Items to Review" still shows the true
total, not the page size; queue re-queries per action so the next items surface automatically.
Verified across three states: queue larger than page size, smaller (banner correctly hidden — no
"5 of 5"), and empty.

Also explains accept-slower-than-reject: same expensive reload, but accept does more writes first
(master record, investor links, auto-rejecting same-company duplicates).

---

## Open threads / where to pick up

**Awaiting Sam:**
- **European Google Alerts** — check Region ("Any region") and How many ("All results") settings;
  run the English-query diagnostic. Send RSS URLs and they get wired in with `skip_relevance_filter`.
- **`TRIAGE_PAGE_SIZE = 20`** is a guess — one-line change to 10 (faster) or 50 (more context).

**Reassess in a few days (Sam's call):** whether the 3 English + 4 local-language European feeds
actually lift the European deal count, and whether Sifted / Augen geradeaus / Opex360 /
Portail de l'IE (all broader than pure trade press) generate triage noise. `scripts/verify_feeds.py`
is the existing tool. The feed-health canary now watches scrape rates automatically.

**Known, not done:**
- **AJAX accept/reject** — the remaining triage-speed win: remove the card client-side instead of
  reloading. Near-instant, but a bigger change to a daily-use screen; not done unprompted.
- **`$` deal indicator only matches glued to a preceding char** (`US$1.8bn` yes, ` $100M` no) —
  pattern is `\b\$\b`. Affects every feed. Untouched.
- Deal-splitting for multi-deal articles (needs live schema change; own session).
- Direct-feed scrape failures (~5 of 18 on a normal day) — time-boxed look worthwhile.
- Country-only locations (`"UK"`, `"France"`) geocode to a country centroid, so deals stack on one
  point. Fix is upstream in the summarizer prompt, not the geocoder.
- Map State/District dropdowns remain US-only by nature; a country filter would be the Europe analogue.

**Health at session end:** 16 feeds enabled (14 direct + 2 Google Alerts, 0 Google News). Pipeline
green. Triage app healthy post-deploy. Public site published with the region filter live.
