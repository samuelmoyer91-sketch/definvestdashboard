# 2026-07-27 — Wiring in the European Google Alerts feeds

Short session. Closes the one item left open at the end of 2026-07-26: the
European Google Alerts feeds Sam created were never added to the config.

## What was done

Added three Alerts feeds to `config/feeds.json` (commit `fd3d9ac`):

| Feed | Language | `skip_relevance_filter` | Entries at creation |
|---|---|---|---|
| Alert: German Defense Industry (DE) | German | `true` | 0 → **2** |
| Alert: French Defense Industry (FR) | French | `true` | 0 |
| Alert: Central/Eastern European Defense | English | `false` | 0 |

Enabled feed count: **16 → 19** (14 direct + 5 Alerts).

## Key finding: an empty new Alerts feed is not a broken query

Yesterday the German alert's preview said "There are no recent results for
your search query" and the feed returned 0 entries, which read like a broken
query — we spent time yesterday testing whether the German terms were the
problem. Today the same URL returns 2 entries with nothing changed.

**New Google Alerts take hours to populate.** The preview pane is not a
reliable test of whether an alert works. Verify with the feed URL over a day,
not with the preview at creation time. This is why the French and CEE feeds
were enabled at 0 entries rather than held back — they returned HTTP 200 with
valid feed structure, which is the real signal.

## Why the CEE feed does not skip the relevance filter

The German and French queries are in their own languages, and the stage-1
keyword scorer matches English word stems — German headlines score ~0.00 and
auto-reject before the AI screener ever sees them. That is the whole reason
`skip_relevance_filter` exists.

The CEE query is written in English ("Polish defence industry", "Baltic
defence"), so the scorer works on it normally. `defence` and `nato` were added
to `keywords.high_priority` on 2026-07-26, so these headlines will score. Left
the scorer on deliberately — it is free noise protection, and the two existing
US Alerts feeds show why that matters (9% and 17% accept rates).

## Watch item: money words in the second OR-group

The German alert's first two items were both noise:

- *"Lynas Rare Earths Aktie: 30-Milliarden-Won-Deal mit LS Eco Energy"* — a
  Korean rare-earths story, matched on `Milliarden`
- *"Business-Liveticker: Abgeordnete verlangen wegen OpenAI 'Kill Switch'"* —
  matched on something in the second group, not defense at all

Both queries have the shape `(industry terms) AND (deal verbs OR bare money
words)`. Bare `Millionen`/`Milliarden`/`millions`/`milliards` are weak
discriminators — nearly any business story contains one. Combined with
`skip_relevance_filter`, everything these feeds return goes straight to AI
screening.

That is tolerable (the AI screener is the real filter and costs fractions of a
cent per item), but if accept rates stay near zero, retighten to drop the money
words:

```
"Rüstungsindustrie" (Investition OR Übernahme OR Finanzierung)
```

## Open

- Reassess in a few days with `scripts/verify_feeds.py`: do the three Alerts
  feeds plus the four German/French direct feeds lift the European deal count,
  and do they add unacceptable triage noise?
- Sam to confirm Alerts settings on each: **Region = "Any region"**,
  **How many = "All results"**.
- Unchanged from yesterday: `\b\$\b` regex bug (affects every feed),
  deal-splitting needs a schema change, country-centroid pin stacking on the
  map, State/District dropdowns are US-only.
