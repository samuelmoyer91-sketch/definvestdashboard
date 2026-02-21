# 2026-02-11 — Rebrand Public Dashboard to Company Colors

## Objective
Align the public GitHub Pages dashboard with Sam's company color scheme to enable future integration with the company site.

## Color Palette

| Role | Old (Teal) | New | Hex |
|------|-----------|-----|-----|
| Primary | `#226E93` | Deep navy | `#1e456e` |
| Dark variant | `#1a5573` | Dark navy | `#162f4d` |
| Light/Tertiary | `#2a87b3` | Lighter blue | `#5d7890` |
| Accent | `#88c0d0` | Bright green | `#88c540` |

## Files Modified
- **`github_site/css/style.css`** — CSS variables renamed (`--primary-teal` → `--primary-blue`, etc.), all values updated, hardcoded rgba colors replaced
- **`github_site/js/main.js`** — `chartColors` object updated, chart fill color lightened
- **`src/export/generate_chart_pages_v2.py`** — Hardcoded `#226E93` and rgba values in generated HTML templates replaced
- **`github_site/index.html`** — Inline `var(--primary-teal)` references updated
- **All 17 chart pages + 3 category pages + deal tracker** — Regenerated from updated templates

## Key Design Decisions

### Green as accent spice, not fill
Sam's feedback: bright green (#88c540) looks ugly as big blocks of color. Final approach uses green *only* for thin/small elements:
- Nav logo + link hover text
- Active nav tab underline (thin line)
- Card h2 accent borders (thin line)
- Key insights border + bullet markers
- Deal analysis border
- Page header top border (thin 3px line)
- Search/filter focus rings
- Deal type labels (small uppercase text)
- Footer links
- Link hover color globally

### Navy handles all solid fills
- CTA buttons (`.btn-primary`)
- Button hover states
- Nav bar background, footer
- Table headers
- Data summary gradient
- Pagination controls

### Other refinements
- `.btn-secondary` → navy outline/ghost style (distinct from primary)
- Page headers → green top border accent
- Chart fill area → lighter blue (`rgba(93, 120, 144, 0.12)`) instead of heavy navy, keeps charts airy
- Key insights / deal analysis backgrounds → faint green tint (`#f4faf0`) to match green borders
- Deal type labels → darker green (`#5a9a2a`) for better legibility on light backgrounds
- Stat card values → lighter blue for visual variety

## Scope
Public site only (GitHub Pages). Triage app and email templates unchanged.

## Not Modified
- `src/export/export_to_html_v2.py` — Uses CSS classes only, no hardcoded colors
- Neutral colors (grays, whites, text, success/warning/error states) — unchanged
