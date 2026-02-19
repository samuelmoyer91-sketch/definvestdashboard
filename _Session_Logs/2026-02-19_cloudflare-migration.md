# 2026-02-19: Cloudflare Pages Migration & Cleanup

## Cloudflare Pages Setup
- Created Cloudflare account (already done by Sam), purchased domain `capitalfordefense.com`
- Created Cloudflare API token with Pages Edit, Account Settings Read, DNS Edit permissions
- Created `capitalfordefense` Pages project via API
- Initial direct-API deploy script failed (manifest format issues); switched to `wrangler` CLI
- Installed Node.js via Homebrew to enable `npx wrangler`
- Deployed via `wrangler pages deploy github_site --project-name capitalfordefense --branch main`
- Added custom domains: `capitalfordefense.com` and `www.capitalfordefense.com`
- Set up CNAME DNS records (proxied through Cloudflare)
- SSL certificates provisioned automatically via Let's Encrypt

## Workflow Migration
- Updated `.github/workflows/publish.yml`: replaced `peaceiris/actions-gh-pages` with `cloudflare/wrangler-action@v3`
- Added GitHub secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`
- Tested full pipeline (generate_site.py → wrangler deploy) — completed in 1m23s
- Updated `update_workflow.sh`: replaced `git subtree push --prefix github_site origin gh-pages` with `gh workflow run publish.yml`

## Generator Template Fixes
- Updated `src/export/generate_chart_pages_v2.py` (both chart page and category page templates):
  - Added B3 logo SVG (24px, white) to nav `.logo` link
  - Added `<link rel="icon">` for favicon
  - Removed inline `color: #666` on source text (CSS handles it now)
- Updated `src/export/export_to_html_v2.py` (deals page template):
  - Same logo SVG and favicon additions

## Cleanup
- **Deleted** `_deploy_cloudflare.py` — contained hardcoded Cloudflare API token; superseded by wrangler workflow
- **Deleted** `github_site/.nojekyll` — GitHub Pages artifact, unnecessary for Cloudflare
- **Updated 9 stale URLs** across README, generate_site.py, docs, and update_workflow.sh:
  - `samuelmoyer91-sketch.github.io/definvestdashboard/` → `capitalfordefense.com`
  - `samuelmoyer91-sketch.github.io/defense-dashboard/` → `capitalfordefense.com`
- **Updated** CLAUDE.md: Key services, deployment details, corrections & learnings

## Token Rotation Needed
- The Cloudflare API token was briefly in `_deploy_cloudflare.py` (now deleted, but in git history)
- Sam needs to rotate the token in Cloudflare dashboard and update the GitHub secret

## Decisions
- Kept `gh-pages` branch for now (harmless historical artifact)
- `update_workflow.sh` retained and updated (useful for manual local workflow)
- Design drafts kept in `_design_drafts/` (active reference material)
