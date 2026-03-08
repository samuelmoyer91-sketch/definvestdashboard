# Session Log — 2026-03-04
## Telegram Bot Fix & AI Disclaimer

### Issues Addressed

**1. Telegram Bot Not Working**
- Root cause: Webhook was registered to an old Railway URL (`web-production-71552.up.railway.app`) that returned 404. Railway had changed the service URL to `capitalfordefense.up.railway.app` at some point but the webhook was never updated.
- Immediate fix: Re-registered webhook via Telegram API to correct URL.
- Long-term fix: Added `register_telegram_webhook_on_startup()` startup event in `src/web/app.py` that uses `RAILWAY_PUBLIC_DOMAIN` env var to self-register on every deploy. Will self-heal automatically if URL ever changes again.

**2. AI Disclosure Disclaimer**
- Added to all four public pages: `github_site/index.html`, `github_site/deals/index.html`, `github_site/charts/indicators.html`, `github_site/charts/market-overview.html`
- Home page: appears both in the "About" card body and in the footer
- Other pages: footer only
- Deals page had no footer — one was added
- Text: "This dashboard is created and updated with the assistance of AI. All claims should be verified using the linked sources."

### Commits
- `8b6fb4a` — Auto-register Telegram webhook on startup
- `26c8396` — Add AI disclosure disclaimer to all public dashboard pages

### Deployed
- Railway: auto-deploys from main push
- Cloudflare Pages: `publish.yml` workflow triggered manually

### Open Questions
- None
