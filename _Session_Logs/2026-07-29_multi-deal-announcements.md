# Multi-deal announcements — open problem

Noted 2026-07-29. **Not solved.** Recording it properly so it stops getting
re-discovered and re-deferred.

## The problem

One article often announces several investments in several places. A
`master_list` row holds **one** location, **one** amount, **one** date.

Real example from the queue (BAE Systems):

> BAE Systems is expanding U.S. munitions production with a **$135 million**
> investment in **Texas and New Hampshire** facilities, a completed
> 150,000-square-foot **Endicott, New York** expansion, and a new **Utah**
> site for ICBM sustainment and modernization engineering work. It is also
> investing **over $300 million over five years** at its **Hägglunds facility
> in Sweden** to expand combat vehicle production capacity, alongside progress
> on THAAD seeker production, the Epoch 2 missile-warning satellite,
> Dreadnought submarines, GCAP, and the Brontanax collaborative combat
> aircraft prototype.

That is roughly six announcements, two continents, at least two distinct
dollar figures, and a tail of programme-progress mentions that are not
investments at all. It currently stores as one row and one map pin.

## Two fixes, and they are not the same thing

**1. Multi-location** — a `deal_locations` child table
(`master_item_id`, `location`, `lat`, `lng`, `note`), with the map reading
from it. Contained. No schema change to amounts, so it **cannot introduce
double-counting**. Fixes the *map*.

**2. Deal-splitting** — separate `master_list` rows per sub-deal, each with
its own amount. Fixes the *record*, and is much harder:

- the AI has to split reliably, and decide what counts as a distinct deal
- jointly-stated amounts need an apportionment rule ("$135 million in Texas
  **and** New Hampshire" — one deal in two places, or two deals?)
- programme mentions (THAAD, GCAP, Dreadnought) are not deals and must not
  become rows
- split rows will look like duplicates of one another, so `dedup.py` needs
  revisiting at the same time

## The trap

Multi-location on its own renders BAE as five pins **all carrying the same
amount**. For anyone reading the map that is arguably worse than one pin. So
it is fine to ship — but as a geography fix, never described as a fix for
roundup articles.

## Recommendation

Build the locations table first: real value, low risk, no effect on capital
totals. Treat splitting as its own session, starting with an explicit written
rule for apportioning jointly-stated amounts, and budget for `dedup.py` work
alongside it.

## Related

- Deferred previously in `_Session_Logs/2026-07-26_*` and
  `_Session_Logs/2026-07-28_published-dup-removal.md`.
- Country-centroid pin stacking is a separate, smaller map issue.
