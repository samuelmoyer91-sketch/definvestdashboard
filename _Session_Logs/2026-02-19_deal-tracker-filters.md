# 2026-02-19 — Deal Tracker Sector & Capital Type Filters

## Changes Made
Added sector and capital type dropdown filters to the deal tracker page (`/deals/`).

### Modified file: `src/export/export_to_html_v2.py`

1. **Moved sectors/capital_sources extraction earlier** in `generate_deal_card()` so values are available for both data attributes and display
2. **Added `data-sectors` and `data-capital` attributes** to each `<div class="deal-card">` — slugified, comma-separated for multi-value sectors
3. **Added two `<select>` dropdowns** (`#sectorFilter`, `#capitalFilter`) inside `.briefing-controls` after the search box
4. **Extended JS filtering logic:**
   - `populateFilters()` IIFE scans all cards on load, extracts unique sector/capital slugs with counts, populates `<option>` elements alphabetically
   - `filterDeals()` now combines text search + sector + capital filters
   - Added `change` event listeners on both selects

### No CSS changes needed
`.filter-select` class already existed in `style.css` (lines 663-676) with matching styles.

## Verification
- Ran `python3 src/export/export_to_html_v2.py` — 90 deals exported successfully
- 89 of 90 cards have data-sectors attributes (1 card likely has no sector data)
- Dropdowns populate dynamically with counts
- Filters combine with search and pagination
