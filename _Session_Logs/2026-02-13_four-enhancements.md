# 2026-02-13: Four Dashboard Enhancements

## Changes Implemented

### Change 1: Edit Accepted Deals
- Created `src/web/templates/edit.html` — full edit form pre-populated from MasterItem
- Added `GET /edit/{master_id}` and `POST /edit/{master_id}` routes in `app.py`
- Added "Edit" button to each item in `master.html`

### Change 2: Editable Title Field
- Added `title = Column(String)` to MasterItem model
- Created `src/database/migrate_add_title.py` migration script
- Added title input to triage.html accept form (pre-populated from RawItem.title)
- Title field included in edit.html
- `POST /accept` now saves title
- `master.html` displays `item.title` when available, falls back to `raw_item.title`
- `export_to_html_v2.py` uses `master.title` when available, falls back to `raw.title`

### Change 3: Remove Broken Deal Type Filter
- Removed `<select id="dealTypeFilter">` from `export_to_html_v2.py`
- Removed `dealTypeFilter` JS variable, event listener, and filter logic
- Search bar retained (works correctly)

### Change 4: Investor Tracking Foundation
- Created `Investor` model (name, slug, deal_count, first_seen, last_seen)
- Created `DealInvestor` join table (master_item_id, investor_id, is_lead)
- Created `src/utils/investor_parser.py` with `parse_investors()` and `slugify()`
- Created `src/database/migrate_add_investors.py` migration
- Created `src/database/seed_investors.py` to backfill existing deals
- Added `_sync_investor_links()` helper in app.py (used by accept + edit routes)
- Added `GET /investors` route + `investors.html` template (table sorted by deal count)
- Added "Investors" nav link to `base.html`
- Updated `__init__.py` exports with Investor + DealInvestor

## Files Created
- `src/web/templates/edit.html`
- `src/web/templates/investors.html`
- `src/utils/investor_parser.py`
- `src/database/migrate_add_title.py`
- `src/database/migrate_add_investors.py`
- `src/database/seed_investors.py`

## Files Modified
- `src/database/models.py`
- `src/database/__init__.py`
- `src/web/app.py`
- `src/web/templates/base.html`
- `src/web/templates/triage.html`
- `src/web/templates/master.html`
- `src/export/export_to_html_v2.py`

## Next Steps (Before Deploying)
1. Run migrations: `python3 src/database/migrate_add_title.py` + `python3 src/database/migrate_add_investors.py`
2. Seed existing investor data: `python3 src/database/seed_investors.py`
3. Test locally: `uvicorn src.web.app:app --reload`
4. Regenerate public site: `python3 generate_site.py`
5. Deploy: push to Railway (triage app) + run publish workflow (public dashboard)
