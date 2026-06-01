# Session Log — 2026-05-31
## Health Check #2 + Duplicate Detection + PE Commentary Fix

### Health check findings (19 days after the 5/12 Rock 1 fix)

**Pipeline: green.** Ingest 20/20 success, publish 12/12, site current to 5/31. ~2.3 deals/day published. 333 deals live (was 289 on 5/12).

**Rock 1 (title screener loosening) worked.** The marquee test — Anduril's $5B Series H (May 13), the biggest defense raise of the month — is on the dashboard. So are True Anomaly ($650M), Scout AI ($100M), Picogrid ($45M), Observable Space ($90M). The VC-round category that was bleeding pre-5/12 is now flowing.

**Misses: now modest.** Candidate misses this month: Kela ($200M, Israeli), Airis Labs ($31M Series B, May 27 — likely still in queue), Senior plc/Blackstone (£1.4B PE take-private, UK-listed). Helsing ($1.2B) correctly excluded as speculative ("in talks"). ~2-3 soft misses vs ~15 marquee deals — big improvement. The international/UK ones reinforce the RSS-feed-strategy priority.

**False positives at the published level: low.** No junk in the published set. One bad source URL (GKN Aerospace card sourced from jezebel.com — Google News mis-resolution, cosmetic).

### Finding #1 — Duplicates (the headline)

~12 clear duplicate clusters where the SAME deal appears as multiple cards, double-counting capital. Root cause: ingest dedup keys on exact-URL match (`rss_fetcher.py`), so the same deal from two outlets = two cards; and announcements spaced days apart arrive in separate triage batches so Sam doesn't catch them.

Clear clusters: Karman Space & Defense (×3, same $28.5M Utah facility), Hadrian ($200M), Safran-Belgium ($144M), Unified Legacy ($125M), Pilatus ($50M), AeroVironment-Albuquerque ($30M), Collins ($26.5M), Dominion ($21M), Integrate ($17M), Firehawk ($16.5M), plus no-dollar pairs (Velocity One/Kaney, Chimney Rock/UEC). Est. ~$550-690M double-counted.

NOT duplicates (legitimately distinct, same company): GE Aerospace ×12 (different facilities), Anduril ×3 (raise/acquisition/facility), CesiumAstro ×3, L3Harris ×2, Ondas ×3.

### Shipped this session

1. **PE commentary fix** (`5e6213b`) — `src/utils/ai_summarizer.py` field #9 now instructs: for acquisitions/PE deals, write strategic_significance from the TARGET company's perspective (what it can now build/expand), never "this helps [firm] build out its platform." Sam's explicit preference. Affects newly-summarized deals.

2. **Duplicate detection tooling:**
   - `src/utils/dedup.py` — shared pure-logic module (no DB). Tuning knobs: `WINDOW_DAYS=30`, `AMOUNT_TOLERANCE=0.05`, `NAME_NOISE`. **This is the single place to tune matching.**
   - `scripts/find_duplicates.py` — CLI report (`b06dbbe`, refactored in `f6dafbe` to use the shared module).
   - `/duplicates` route + `duplicates.html` template + "Duplicate Check" nav link in `base.html` (`f6dafbe`). **Read-only** page in the triage app: lists likely-dup clusters, each row linking to its `/edit/{id}` page. Matched cards marked »; distinct same-company groups (GE etc.) in a collapsible section.

   Design decision: built INTO the triage app (not just a CLI) because Sam won't remember a command — it needs to be in his standard workflow. The nav link shows on every page. Logic shared between CLI and web so there's one place to tinker without breaking anything (the route only reads master_list).

All pushed to `main` (through `f6dafbe`). Railway auto-redeploys the triage app; PE fix hits next ingest.

### Standard-process note for future health checks

**The duplicate check is now a standard step.** When running a periodic health review, pull the `/duplicates` report (or `python3 scripts/find_duplicates.py` with creds) as part of it. Sam cleans up confirmed dups via the edit UI.

### Open / deferred (unchanged priority)

1. **Direct-publisher RSS feed strategy** — still the top queued big rock (coverage gaps, empty cards, dead-weight feeds). See `project_current_state.md`.
2. **Ingest-time dedup upgrade** — the `/duplicates` page is detection/cleanup after the fact. A future improvement: warn at triage time when an incoming item matches an existing master_list deal (company+amount+window), using the same `dedup.find_clusters` logic. Natural next step once Sam trusts the matching.
3. **Backfill cleanup** of the 163 empty stub records (5-min one-off).
4. **rejection_reason capture** in triage UI (93% NULL).

---

## Direct-publisher RSS feed rollout — STAGED, in progress (started 2026-05-31)

### Why (recap)
Source analysis of 335 published deals: all 8 active feeds route through Google News (the middleman behind empty-card scrapes, coverage gaps, latency). Direct publisher feeds carry REAL article URLs (`feedparser` reads `<link>` generically in `rss_fetcher.py`), so they scrape cleanly and bypass Google. Source distribution is long-tailed (211 domains for 335 deals, 74% appear once) — so direct RSS won't cover the local-business-journal long tail, but it captures the addressable high-value layer: defense trade press + newswires + funding trackers. Premier outlets (Breaking Defense, Defense News, DefenseScoop) barely appear in current data — strong sign Google under-surfaces them.

### Important framing correction (for accurate expectations)
The funnel has three very different numbers. Earlier in the session I sloppily conflated them. Real funnel (from 5/12 health check, 90d):
- **Raw ingested (pre-filter):** ~42/day now
- **Reach triage (after keyword + AI title filters):** ~5/day now (458/90d)
- **Published (Sam accepts):** ~2.3/day now

Adding feeds mostly inflates the RAW number; the triage queue and published counts rise modestly. Sam will NOT see "100/day" anywhere — that confusion came from me summing the feeds' visible item-windows (snapshot buffers, ~134 items) and mislabeling it as daily flow. **We do not actually know the net daily new-item rate from these feeds yet — that's the #1 thing Phase 1 measures.** Rough guess post-rollout: raw ~85-110/day, triage ~10-20/day, published ~3-5/day. Verify, don't trust the guess.

### Cost impact
Negligible. Title screener is Haiku at ~$0.00025/item. Even +150 raw/day = ~+$1.30/mo.

### Phase 1 — LIVE NOW (3 tight, proven feeds; committed `<this session>`, config/feeds.json)
- **Direct: PR Newswire Aerospace & Defense** — category-filtered newswire, deal-first, tight
- **Direct: GlobeNewswire Aerospace & Defence** — same
- **Direct: SpaceNews** — #1 proven source (13 deals); the one full-site feed in Phase 1, so its volume/noise is the main watch item

All 3 verified returning live RSS items. Real article URLs.

### Phase 2 — STAGED OFF (enabled:false in config/feeds.json, ready to flip on)
- **Direct: Breaking Defense**, **Direct: Defense News**, **Direct: DefenseScoop** — premier full-site feeds, enable together after Phase 1 proves out
- **Direct: Pulse 2.0** — VC funding tracker (13 deals) but NOT defense-specific = noisiest; enable LAST and watch accept rate

### COMPLETION CRITERIA — measure after ~1 week of Phase 1 (need Turso creds / or query live), then complete Phase 2
Check the following on `raw_items` where `feed_source LIKE 'Direct:%'`:
1. **Flow:** Are the 3 feeds actually producing raw_items? (sanity — confirms ingest reads them)
2. **Net daily volume:** raw items/day from the 3 feeds (the number we don't know yet).
3. **Clean scrapes:** confirm `article_content.clean_text` length is healthy (NOT the ~11-char "Google News" stubs) — this validates the whole premise that direct URLs scrape cleanly.
4. **Reach-triage rate & accept rate:** how many got to triage, how many Sam accepted. Compare signal vs the Google feeds.
5. **Duplicate impact:** check `/duplicates` — did direct feeds create many new clusters (same deal via Google + direct)? Expected yes in interim; quantify.
6. **New catches:** did the direct feeds surface any deal the Google feeds missed? (the upside test)

**If Phase 1 looks good** (clean scrapes confirmed, manageable volume/noise, real catches): flip Breaking Defense + Defense News + DefenseScoop to enabled:true (Phase 2), re-measure ~1 week, then add Pulse 2.0 last.

### Phase 3 — LATER (after direct feeds prove out)
- **Retire dead-weight Google feeds:** Carlyle Defense (0% accept), Defense Corporate Ventures (0% accept).
- **Rewrite New Factory Defense Products query:** drop "expansion" and "military" noise vectors.
- **Fix In-Q-Tel:** keyword scorer kills 66% of IQT items before AI screening — needs IQT-specific handling.
- **Structural sources (separate ingest paths, more work):** SEC EDGAR 8-K filings (every public-company M&A/material event, day-of, machine-readable), SAM.gov (industrial-base contract awards), Business Wire defense category (verify RSS — not yet checked).
- **Endgame:** once direct feeds cover the high-value layer, retiring Google feeds makes duplicates go DOWN (clean canonical URLs, no redirect dups).

### Do NOT
- Re-attempt the Google News URL resolver (reverted `f447bb0` — cloud IPs blocked by Google). Direct RSS is the superset solution.
