# 2026-10-07 — Triage app usability review (all pages, phone first)

Sam: "review the triage page for user friendliness, especially on a phone.
Check out all pages to make sure they are well organized, simple and clean.
Make sure they'd work for the most common uses."

Treated as a review with recommendations (as with the 2026-09-24 phone review
and the site health check), not a build.

## Method
- App run locally (uvicorn, no auth env → auth skipped) against a scratchpad
  copy of the July 27 local replica. Data is stale, so layouts are real but
  counts are not. Live app is behind Basic Auth; not logged into.
- Each page measured in the browser pane at 375×812 and at desktop width.
- Local copy had schema drift (no `split_instruction`) — patched the scratch
  copy only. Loaded the 1,029-deal export (export.yml run 37713296704) into it
  so list pages have real volume. Investors were rebuilt with the app's own
  `_sync_investor_links`, so the parser findings reflect production behaviour.

## Findings (measured)
Daily triage (~21 decisions/day, ~2/3 rejects):
- **Screen jump after a decision.** Accept from the pinned bar after scrolling
  into the form: card hidden, scroll position unchanged, so the view lands ~4
  cards further down (accepted card 3; visible after: cards 8–11).
- Collapsed card shows headline, feed-alert name, date, amount + first sector.
  No company, location or one-line summary, so most rejects need the card opened
  (expanded card 1,991px, 34 checkboxes) or the original article.
- First card starts 380px down (header + two count boxes; "Items in Master
  List" is not a triage number).
- Open card switches headline from the AI title to the raw feed title
  (triage.html:209 vs :174).
- Reject = 3 taps (Reject → reason → Reject). Couldn't check how often more than
  one reason is used: the local copy has no reasons (Feb data).

Duplicates:
- Possible Dups "view" (the already-published match) → `/edit/{id}` → redirect
  to the top of the 25 MB Accepted Items page, not the deal.
- Two nav entries, "Possible Dups" and "Published Dup Check", read as the same.

Finding / fixing a published deal:
- `/master`: 25 MB HTML, 172k DOM nodes, ~960,000px tall at 375px; every deal
  ~900px including an internal "Pipeline Status" box; a hidden full edit form per
  deal; no search; 3 DB lookups per deal.
- `/rejected`: all rejections ever, each with full article text; no "restore"
  (`/restore` only handles Excluded items). A wrong reject can't be undone in the app.

Broken:
- 13/22 sector pages 404 (name contains "/"; even %2F is decoded by routing).
- Investors: "Inc." (10) and "Unknown" (13) listed as investors; ✕ delete is
  21px beside every row on phones (has a confirm()).
- Costs page model labels stale; Sonnet 5 rate per pricing.py's own comment
  changed 2026-08-31 and the table wasn't updated (unverified).

Phone polish: Sectors (575px), Costs (445px), investor detail (504px) tables
overflow; item-detail and map inputs <16px (iOS focus zoom); Menu button 30px;
12 nav links, no grouping, no current-page highlight.

Recommendations given to Sam in chat, grouped A–D; awaiting choice. Logged as
OPEN_ITEMS #20.

## Sam's cut, and what was built (A + B)
Sam: A2 wrong (opening a card is easy), keep A4 (the raw headline in an open
card gives a second view of the deal), drop A5 except "reject without a
reason", skip D11 for now, D13 "definitely needs review", C and D later today.

Built and tested locally (scratch DB, 375px):
- **Screen jump:** `takeCard` scrolls by the hidden card's offset when its top
  was above the screen. Accepting card 3 from the bottom of its form now leaves
  card 4 at the top (was card 8).
- **Count in the heading:** "Triage Queue · N to review"; master-list box and its
  per-load count query removed. First card 380px → 295px down.
- **Reject with no reason:** popup says "Optional"; nothing ticked posts no reason.
- **Sectors:** `/sectors/{sector_name:path}`; AI/ML, Space/Satellites etc. 200.
- **Edit page:** `GET /edit/{id}` renders the existing `edit.html` (it had been a
  redirect to the top of /master). Save and Cancel return to the referring page;
  `_local_path` refuses off-site referers and `//host` tricks (tested).
  16px fields on phones so iOS doesn't zoom.
- **Names:** "Dups: In Queue" / "Dups: Published" in the nav and page headings.

## A+B pushed (`6a56938`); C built
- **Accepted Items** (`/master`): compact rows (title / amount · company · place ·
  accepted date), each opening `/edit/{id}`; search across title, company,
  investors, location, sectors, capital type, amount; 50 per page. One query
  plus a joined load instead of 3 lookups per deal. Locally: 25 MB → 26 KB,
  ~960,000px → ~3,800px tall. The inline edit forms are gone; `edit.html` is the
  one edit form now (master.html no longer posts to /edit).
- **Rejected Items**: search headline or reason, 50 per page, "Restore to queue"
  (`POST /rejected/{id}/restore` deletes the rejected_items row). Article text
  no longer embedded; the headline opens `/item/{id}`. Tested: a restored item
  reappears in the triage queue and leaves the list.
- Old headlines with `<b>` tags / `&amp;` (pre-cleaning feed titles) now go
  through `striptags`; the old page rendered them as HTML with `| safe`.
- Saving an edit returns to the list page you came from, search included.

## C pushed (`880b694`); D built
- **D12 Costs:** checked Anthropic's published rates (claude-api reference,
  cached 2026-10-06): Sonnet 5 is $2/$10 per MTok, so `pricing.py` was right and
  my review's "costs understated since Sept" warning was wrong — the stale part
  was the code comment claiming an intro price. Haiku 4.5 corrected to $1/$5
  (no longer used). Page labels now say Sonnet 5 for both steps.
- **D13 phone polish:** grouped menu (Daily / Deals / Explore / Admin) with the
  current page highlighted; 44px Menu button; every field 16px on phones (global
  rule, stops iOS focus-zoom); Sectors hides two wide columns on phones; Costs and
  investor-detail tables scroll inside their card; Investors table tightened.
  All 16 pages measured at 375px: none wider than the screen.
- **Item detail:** the legacy "Accept & Curate" form now shows only for undecided
  items. Accepted → "Edit this deal"; removed → link to Removed; rejected → reason
  and pointer to Restore. Submitting it on an accepted deal would have re-accepted
  it with the form's older fields.
- **Edit form data bug (pre-existing):** sector labels were a 13-item list
  beside 22 values since the 2026-07-04 taxonomy expansion, so most boxes were
  labelled with the wrong sector (in the old /master inline editor too). Capital
  types in `edit.html` lacked Government Support, Corporate Venture, Family Office,
  Strategic Partner (and offered "Government/Contract"), so saving dropped them.
  Rebuilt both as the triage lists; legacy "Government/Contract" shows as
  Government Support. Round-trip tested: load → save unchanged → identical row.

## D pushed (`05a4174`, Railway deploy success). Sam's next three issues
Sam: (1) many cards lack a location and he won't accept without one, so he looks
them up; (2) the AI sometimes writes "the article did not have X", which he
fears accepting unnoticed; (3) what happens with an ambiguous investor? He'd
rather it be empty. Asked for ideas; investigated, nothing built yet.

How it works today: the AI's values go straight into the form boxes (no
clean-up); the prompt says 'use "Unknown" if not found' and nothing forbids
commentary; whatever is in a box is saved on Accept. Investors are split into
investor records on accept with no placeholder filtering.

Measured on the 1,029 published deals (export 37713296704):
- 75 published with no location (blank or "Unknown"); 2-6% a month since July,
  6 already in October (#1118/#1119 Ondas acquisitions, #1061 Flow Engineering,
  #1057 Armadin, #1019, #1020). So the "no location, no accept" rule is slipping,
  mostly on small acquisition targets and startups. An empty box shows grey
  example text "e.g., Austin, TX, USA", which reads like a value on a phone.
- Reusing a company's earlier location is a bad fill: only 23% of deals are
  repeat companies and the earlier city matched in 27/135 — Sam records where the
  money goes (facility), not HQ. Ruled out.
- 2 published summaries carry notes: #94 "Unknown - article content not
  accessible due to paywall restriction", #1117 "...not detailed in available content."
- 14 published deals have investor "Unknown" (it is an investor record with 13
  deals); generic groups ("Institutional investors", "family offices") also
  became records. parse_investors keeps "Unknown", "N/A", "Undisclosed
  investors" and whole phrases like "Valor Equity Partners and other
  undisclosed investors" as single investors, so that deal is missing from
  Valor's page. Public site hides "Unknown" (is_known) but not the phrases.
- Web search for an automatic location lookup: $10 per 1,000 searches plus
  tokens — estimated 3-5¢ per lookup.
- Dead code found: GET /api/action (email approve links) creates deals with no
  location or title; nothing generates those links any more.

Wrote `scripts/extraction_quality.py` (read-only): AI blank-location rate by
deal type and what happened to those cards, notes-about-missing-info by field,
investor placeholders. Tested on the Feb local copy (runs; data too old to
mean anything). Needs a push to run on live data. Recommendations to Sam in chat.

## Report run (36716270958 -> run 37716270958) and build
Live, last 30 days, 1,047 extractions: AI left location blank on 61 (6%):
acquisitions 17%, mergers 38%, funding rounds 12%, everything else <5%. Of the
61: 38 rejected, 14 pending, 8 ACCEPTED WITH NO LOCATION, 1 typed in. Notes about
the article: 22 summaries (2%, 2 accepted), always a trailing ", though ... not
disclosed in available reporting." clause. Investors: 80 "Unknown", 15 blank.
Decision: automatic web lookup (1c) NOT built — ~2 cards a day, and the slips
are a review problem, not a volume problem.

Built (`cd76c0d`, not yet pushed), Sam: "go with your recommendations":
- `src/utils/field_hygiene.py`: is_placeholder / clean_value, strip_source_notes
  (only sentences that name the source AND say something is missing; cuts the
  trailing clause, else drops the sentence; untouched text returned verbatim),
  is_unnamed_group, clean_investor_text (keeps "(lead)").
  Tested: 11/11 note cases; on 1,029 published summaries it changes exactly the
  2 known ones. First version wrongly caught "areas without cellular coverage"
  and collapsed paragraph breaks — both fixed.
- Investor parser drops placeholders/unnamed groups, keeps names inside group
  phrases. 24/24 cases; on all published deals only 22 parse differently, every
  drop a placeholder or group.
- Prompt: null not "Unknown"; named investors only; no comments on the article.
- Applied at save (generate_ai_summaries), display (Jinja filters for cards
  already queued), accept and edit (server side).
- Triage: "No location" tag; red "Location needed" box; Look up button (web
  search for "<company>" headquarters); Accept confirms when location empty;
  investors placeholder "None named" (the grey example read like data).
- `scripts/clean_placeholder_fields.py`: dry run by default. Rewrites investor
  TEXT only when a part is a placeholder/unnamed group (wordy lists like "Led by
  X with participation from Y" keep their wording); rebuilds investor records
  only for deals linked to a junk record or rewritten; then deletes junk records
  with no deals. On the scratch copy: 2 summaries, 24 lists, 22 rebuilds, 9
  records removed; second run finds nothing.

## Shipped
Pushed `411d66f`; Railway deploy success. Live clean-up: preview matched the
scratch run (2 summaries #94 and #1117; 23 investor lists; 22 deals' records
rebuilt, incl. #48 and #51 gaining records for their named investors; 7 junk
records), applied, and a third run found nothing left. The public site picks up
the two summary fixes on the next publish (01:00 UTC). New cards get the new AI
instructions from the next pipeline run; cards already queued are cleaned on display.
