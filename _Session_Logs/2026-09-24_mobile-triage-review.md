# 2026-09-24 — Mobile usability review of the triage queue

Sam reviews deals on a phone in bed and finds the triage page "slightly clumsy".
Asked for a review and ideas — survey only, no changes made this session.

## Method
The live app is behind Basic Auth, so `triage.html` was rendered locally with
three mock deals and measured in the browser pane at 375×812 (iPhone-sized).

## Findings (measured, not guessed)
- **No mobile CSS anywhere.** Zero `@media` rules in `base.html` or `triage.html`.
- **The expanded form is wider than the phone.** The two 4-column checkbox grids
  (`triage.html:217`, `:293`) measure 361px and 569px against ~295px of room.
  The page's layout width became 626px on a 375px screen, so the phone zooms
  the whole page out — that is why everything looks small once a card is open.
- **Inputs are 13px.** iOS Safari auto-zooms on focus for any field under 16px,
  and does not zoom back — the "tap a field, page jumps" behaviour.
- **Tap targets are tiny.** Checkboxes 14×14px, reject-modal checkboxes 15px
  (Apple's guideline is 44px).
- **First deal starts 822px down** — below the fold on an 812px screen. Header
  (274px, 12 nav links wrapping to 4 lines) and two stat cards (270px) eat it.
- **Expanded card is 1,230px tall**, and Accept sits at the very bottom.
- **"$ €300,000,000".** The amount field has a fixed "$" label in front of an
  input that now keeps its own marker (since the 2026-08 currency fix), so
  USD reads "$ $47,000,000" and euros read "$ €300,000,000". Display only —
  the stored value is correct.

Options proposed to Sam in chat; awaiting choice.

## Built: options A + B (Sam chose both)

**A — phone basics.** All phone rules sit behind `@media (max-width: 640px)`;
desktop was compared old-vs-new at 1280px and is unchanged except the two items
below.
- Inline styles on the form fields moved to classes (136 → ~37 `style=`
  attributes in `triage.html`). This was necessary, not tidying: an inline
  style beats any stylesheet rule, so the phone rules could not override them.
- Checkbox grids go to two columns; long labels wrap at the slash (`<wbr>`).
- Fields 16px (stops iOS focus-zoom); checkboxes 22px; buttons 44px tall.
- Header: 12 nav links behind a "Menu" button on phones (all pages).
- Count boxes compacted side by side. Hover-lift restricted to real pointers.
- "$" box hides when the amount carries its own currency. (This one also shows
  on desktop.)

**B — pinned decision bar.** Accept / Reject / Cancel are `position: sticky`
at the bottom of an open card, on desktop as well — harmless there when the
buttons are already on screen. The bar sits outside the form, so Accept uses
`form="accept-N"`. Tested: the pinned Accept, a direct form submit, and Reject
each post the right card's data, and the euro amount survives. Enter-in-a-field
was NOT truly tested (a scripted keypress doesn't trigger it); it relies on
the browser counting a `form=`-linked button as the form's submit button,
which is standard behaviour. The reject popup's buttons are
pinned the same way; the popup was taller than a 667px-high phone.

**Measured at 375px:** page width 626 → 375 (no more zoom-out); first deal
822px → 380px down; header 274 → 86px.

**Testing quirk:** the in-app browser's screenshots go blank once the page
scrolls (a capture artifact — the old page did the same). Worked around it by
scrolling an inner box instead of the page.

## Found in passing → OPEN_ITEMS
- #14 `item_detail.html` still carries the old currency-stripping formatter
  (low exposure — see backlog).
- #15 `edit.html` shows the same "$ €" display quirk.
- C/D (quick accept, swipe) recorded under DECISION.

## Not yet verified
Nobody has tried it on a real iPhone. That's the real test, once it's deployed.

## Later: reject popup trimmed, currency forms unified
- Reject reasons: International dropped; Below threshold + Insufficient detail
  merged as "Below threshold / too thin"; "Not a capital event" (most used)
  moved last, next to the Reject button. Old rejections keep their old labels.
- Currency: the amount-field JS existed in three copies. Now one shared
  `_currency_input.html`. Closes OPEN_ITEMS #14 (item-detail stripped € £) and
  #15 (edit showed "$ €…"), plus a bug found on the way: edit's
  `.replace('$','')` turned `C$10M` into `C10M`. The edit page deliberately
  does NOT reformat on load, so a stored "Undisclosed" isn't blanked unless
  someone edits the field. Formatter checked in node against $, €, £, C$, A$,
  US$, bare numbers.
- Still open: OPEN_ITEMS #0, the 74 European deals stored as dollars. Next.

## Currency data repair, round 1 (OPEN_ITEMS #0) — done, verified
- Key insight: the curated titles still carried the currency, so most repairs
  needed no re-extraction. Scanned all 920 deals; 48 had a non-USD title with a
  `$` amount.
- Sam approved 31 writes: 29 symbol/magnitude restorations + EDF (#699, stored
  10x low) + Airbus (#107, `$530,000` → `$530,000,000`). 17 left alone because
  they had already been converted to USD by hand; adding € would double-convert.
- Mechanism: `scripts/fix_currency_amounts.py` via migrate.yml. It only writes
  if the stored value still equals the reviewed `old` value. The dry run
  matched 31/31, the real run applied 31/31, and a fresh export confirms
  31/31.
- Public site picks the new values up on the next publish (daily 1 AM UTC,
  or `gh workflow run publish.yml`).
- Round 2 (53 deals with no currency in the title) logged in OPEN_ITEMS #0.

## Project status review (Sam asked for a full review + next refinements)
Sources: fresh deals export (925 deals), ingest logs Jun 29 – Sep 24 (every
3rd run), live `/health`, July-5 replica for edit behaviour (Apr–Jul, 299
accepts), and `inspect_failing_text.py`, run for the first time (36083257006).

Findings worth keeping:
- **Refusals root-caused:** 27 of 29 are Sifted. Its paywall scrambles
  everything after the lead paragraph, and the model's safety filter refuses
  the cipher-like text. Refused items are **hidden** from triage (the
  all-Unknown filter) and **retried daily forever**: the pile went 9 → 29 over
  Aug 10 – Sep 24, and it's roughly half the daily extraction spend. Missing
  from master as a result: Uforce, The Exploration Company $450M. See
  OPEN_ITEMS #6.
- Volume: accepts ~70/month (Feb–May) → 183 (Jul), 174 (Aug), 114 (Sep to
  date). Europe is 26% of accepts in the last 3 months (13% before). 68% carry
  an amount.
- Edit behaviour (Apr–Jul): 54% of accepts are taken exactly as the AI
  proposed; company changed 3% of the time, amount 5%. Investor "Self-funded" was
  overridden 21 of 21 times (20 to the company's own name). "Unknown" location
  was hand-filled 29 of 33 times.
- Live, tonight: 20 accepts + 13 rejects in ~7 min on the new phone layout.
  Accept median 1.7s, of which investors 0.64s + autoreject_scan 0.56s; one
  accept took 22s (first click after the deploy).
- Pipeline: 0 failed ingest runs in September; 5 of ~95 since late June,
  all transient.
- Stale: memory `project_current_state.md` (July). Marked stale in the index.
