# 2026-02-09 - Deal Amount Field Standardization

## Changes Made
- **triage.html**: Changed Deal Amount input from free-text to formatted currency input with `$` prefix, numeric-only validation, and auto-comma formatting. AI shorthand values (e.g., "$300M") are parsed into full numbers on expand.
- **item_detail.html**: Same currency input changes. AI values parsed on page load.
- **app.py**: Backend now prepends `$` to the investment_amount before storing in the database.

## How It Works
- Visual `$` prefix is always visible next to the input field
- Input only accepts digits, decimals, and commas
- Numbers are auto-formatted with commas as user types (e.g., "100000000" → "100,000,000")
- AI-extracted shorthand like "$300M" or "$4.7B" is expanded to full numeric format on focus

## Open Questions
- Existing master list items with old-format amounts (e.g., "$300M") will display as-is. May want a migration to standardize historical data.
