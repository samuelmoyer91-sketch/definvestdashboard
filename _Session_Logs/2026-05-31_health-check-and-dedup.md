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
