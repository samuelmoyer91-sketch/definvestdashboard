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
