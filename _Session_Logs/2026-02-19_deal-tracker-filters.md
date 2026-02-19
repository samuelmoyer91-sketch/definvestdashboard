# 2026-02-19 — Deal Tracker Sector & Capital Type Filters

## Changes Made
Added sector and capital type dropdown filters to the deal tracker page (`/deals/`).

### Modified file: `src/export/export_to_html_v2.py`

1. **Moved sectors/capital_sources extraction earlier** in `generate_deal_card()` so values are available for both data attributes and display
2. **Added `data-sectors` and `data-capital` attributes** to each `<div class="deal-card">` — slugified, comma-separated for multi-value fields
3. **Added two `<select>` dropdowns** (`#sectorFilter`, `#capitalFilter`) inside `.briefing-controls` after the search box
4. **Extended JS filtering logic:**
   - `populateFilters()` IIFE scans all cards on load, extracts unique sector/capital slugs with counts, populates `<option>` elements alphabetically
   - `filterDeals()` now combines text search + sector + capital filters
   - Added `change` event listeners on both selects

### No CSS changes needed
`.filter-select` class already existed in `style.css` (lines 663-676) with matching styles.

## Follow-up Fixes

### Multi-value capital types
Capital sources (like "Public Markets, Strategic Partner") were initially treated as a single slug. Fixed to split on commas — same approach as sectors. Both counting and filtering now handle multi-value capital correctly.

### Display labels and alias merging
Replaced the generic `unslugify()` function with explicit label maps for proper capitalization:
- "AI/ML" instead of "Ai Ml"
- "Software/IT" instead of "Software It"
- "Grant/SBIR" instead of "Grant Sbir"
- etc.

Added alias maps to merge duplicate categories:
- **Sectors:** `ai` → `ai-ml`, `materials` → `advanced-materials`, `mineral-refining` → `advanced-materials`
- **Capital types:** `corporate-investment` → `internal-self-funded`, `grant-sbir` → `government-contract`

### Updated README
Updated `github_site/README.md` to describe the new dropdown filters.

## Verification
- Ran `python3 src/export/export_to_html_v2.py` — 90 deals exported successfully
- Dropdowns populate dynamically with correct counts and proper labels
- Filters combine with search and pagination
- Alias merging confirmed: AI and AI/ML show as single entry, etc.
- Deployed to Cloudflare Pages via `publish.yml`
