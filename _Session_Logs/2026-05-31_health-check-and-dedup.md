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

---

## NEXT BUILD (agreed, spec'd, not yet built) — pre-triage "Possible Duplicates" bucket

**Goal (Sam's words):** catch duplicates *before* they reach the triage queue, so he doesn't sort through items only to reject them as dups. Deferred to next session (hit usage limit 2026-05-31); design is locked below — execute from this spec.

### Locked design decisions
- **Option B — separate bucket, not inline banners.** Flagged likely-dup items are filtered OUT of the main triage queue into a dedicated review page. Main queue stays clean.
- **Flag-and-route, NEVER auto-delete.** Auto-rejecting on a match would silently kill real distinct deals (the GE Rutland $42M vs Lynn $42M coincidence — same company/amount/±1 day but different facilities). Every flagged item keeps a one-click "send to queue" escape hatch. This is non-negotiable given Sam's #1 fear (missing deals).
- **Query-time computation, no pipeline/schema changes.** Compute on page load from data that already exists (queue items' AIExtraction company/deal_amount; published master_list company/investment_amount). Mirrors how `/excluded` and `/duplicates` already work. Tuning stays in `src/utils/dedup.py`.
- **Reuse `dedup.find_clusters`** — same matching logic as `/duplicates`. Union the matched pairs into connected components to form one "deal group" per real-world deal.

### What each queue item is checked against
1. Already-published deals (`master_list`) → if already on the dashboard, default action = reject the incoming dup.
2. Other items currently in the triage queue → two outlets, same fresh deal → default = keep best source, reject the rest.

### Grouped review UX (the part Sam cares about — group by DEAL, not a flat list)
- **Type 1 group (matches a published deal):** show the published deal greyed as a non-actionable reference anchor at top; incoming queue dup(s) below with [Reject as dup] / [Keep →] buttons.
- **Type 2 group (queue-only cluster, none published):** show the 2+ queue items together with a "keep the best source, reject the rest" affordance.
- **Three speed features:**
  1. Always show the **match reason** ("same company · ~$28.5M · within 8 days") so Sam can spot coincidences.
  2. Show **location + source outlet prominently in every row** — location is the tell for facility false-positives (Rutland vs Lynn).
  3. **Sort groups by confidence** — exact-amount + same-company + tight-window first; weaker (both no-$, wider gap) lower. Plus a one-line **insight snippet** per card to confirm same event without opening it.

### Implementation checklist
1. `src/utils/dedup.py`: add a helper to union matched pairs into connected components (deal-groups), and a function that takes (queue_items, published_items) and returns grouped dup clusters with type tag (matches-published vs queue-only) + flagged queue-item ids.
2. `src/web/app.py` `home()`: exclude flagged-dup queue items from the main triage query (so they leave the main flow).
3. New route `/possible-duplicates` (or `/dup-queue`) rendering the grouped view.
4. New template (grouped, two group types, per the mockup in this session's chat).
5. POST actions: `reject as duplicate` (→ rejected_items with reason "duplicate of #X"), `keep one / reject rest` (group-level convenience), `send to queue` (false-positive escape → back to main queue). NOTE: this also finally starts populating `rejection_reason` for dups — ties into the deferred rejection-reason gap.
6. Nav link ("Possible Dups" + count badge).
7. Test: dedup grouping logic, template render, each POST action, and confirm flagged items truly leave the main queue and can be restored.

### One open question to confirm at build time
Sam leaned toward wanting the **group-level "keep one, reject the rest"** button (handy for Karman ×3, Integrate ×2). Confirm vs per-item-only before finalizing the template.

### Relationship to other deferred work
- This supersedes/absorbs the earlier "ingest-time dedup upgrade" note — same goal, cleaner (query-time, no schema change).
- It partially addresses the `rejection_reason` NULL gap (dup rejections will carry a reason).
- Best built AFTER the direct-feed Phase 1 lands, since direct feeds will increase interim duplicates — making this bucket more valuable and giving real data to tune against.

---

## BUILT & SHIPPED 2026-06-01 — Possible Duplicates bucket (commit `8642179`)

Built per the spec above. Sam confirmed the open question: **both** group-level "keep one, reject the rest" AND per-item buttons.

### What shipped
- `src/utils/dedup.py`: `find_queue_duplicates(queue_items, published_items)` — union-find groups each queue item with the published deal and/or other queue items it matches. Returns confidence-sorted deal-groups (Type 1 = matches_published, Type 2 = queue_only) + `flagged_ids`. Reuses existing `normalize_company` / `parse_amount` / `amounts_match`. Plus `_match_reason()` helper.
- `src/web/app.py`:
  - `_triage_queue_items(session)` — extracted the shared base queue query (used by `/` and `/possible-duplicates`).
  - `_queue_dup_flagged_ids()` — computes flagged ids, skipping items carrying the keep marker.
  - `home()` — routes flagged items OUT of main queue; passes `dup_count` for a banner.
  - `/possible-duplicates` (GET) — grouped view.
  - `/reject-dup/{id}`, `/reject-dup-group`, `/keep-dup/{id}` (POST) — actions. Dup rejections write `rejection_reason="Duplicate of …"`.
  - `DEDUP_KEEP_MARKER = "dedup_keep"` appended to `RawItem.relevance_flags` (no schema change) when Sam clicks Keep.
- Templates: new `possible_duplicates.html`; banner added to `triage.html`; nav updated — "Possible Dups" (this bucket, next to Triage Queue) + relabeled the prior report "Published Dup Check".

### Design-review risks — RAISED and CONSCIOUSLY ACCEPTED by Sam (2026-06-01)
Did a final critical pass before pushing. Three risks surfaced; Sam chose to ship as-is because **he reviews the Possible Dups bucket every time he triages**, which neutralizes the main one.

1. **(Most important) Type 2 queue-only clusters leave the main queue entirely.** When two outlets report the SAME brand-new (never-published) deal, BOTH copies are routed to the bucket — so a genuinely-new deal appears in ZERO places in the main queue; it lives only in the bucket. Today those show as 2 cards in the main queue (annoying but impossible to miss). **Mitigation Sam relies on: he always reviews the bucket.** If that workflow ever lapses, revisit — the safer alternative is: only remove items that match an ALREADY-PUBLISHED deal (Type 1), leave Type 2 clusters in the main queue and merely surface them in the bucket. That change also simplifies the code (no representative-picking). Documented here so it's not lost.
2. **Weak-signal no-amount matches.** `amounts_match(None,None)` is True, so two no-dollar items match on company + date-window alone. For serial acquirers (Boeing, GE, Anduril, Lockheed) two unrelated no-amount events within 30 days could group as dups and (per risk 1) get held out of the main queue. Keep button recovers them. Tunable later via `dedup.py` if it proves noisy.
3. **Minor:** keep-marker lives in `relevance_flags` — a re-score would wipe it (self-corrects, click Keep again). `home()` loads all `master_list` each page load (trivial at 242 rows; revisit ~2000+).

### Verified before push
dedup logic on synthetic edge cases (Type 1, Type 2, GE Rutland/Lynn false-positive flagged-but-distinguishable via location, solo item NOT flagged); both templates render; all 4 routes register; triage banner shows/hides on `dup_count`.

### Follow-up to watch (next session)
- After a few real triage sessions: is the bucket catching real dups without burying real new deals? Check `/possible-duplicates` group quality and whether anything legitimate got stuck.
- If risk 1 or 2 bites, apply the "Type 1 only auto-removes" simplification from risk 1 above.
