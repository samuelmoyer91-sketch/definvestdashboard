# Quick Reference Card

**Defense Capital Dashboard - Commands You'll Use**

---

## ⭐ Primary Workflow (Use This)

The pipeline runs automatically via GitHub Actions — you only need to triage.

| Stage | Schedule | How |
|-------|----------|-----|
| **Ingest** (RSS fetch, scrape, AI summaries) | Daily 6 AM ET | GitHub Actions (`ingest.yml`) |
| **Triage** (review/accept/reject deals) | Anytime | Railway app at your Railway URL |
| **Publish** (data refresh + site deploy) | Daily 8 PM ET | GitHub Actions (`publish.yml`) |

To trigger either workflow manually:
```bash
gh workflow run ingest.yml
gh workflow run publish.yml
```

---

## 🔧 Common Tasks

### Test Site Locally
```bash
cd ~/Documents/Claude/"PC Dashboard"/github_site
python3 -m http.server 8080
# Open: http://localhost:8080
# Press Ctrl+C to stop
```

### Run Triage App Locally (if Railway is down)
```bash
cd ~/Documents/Claude/"PC Dashboard"
uvicorn src.web.app:app --reload
# Open: http://127.0.0.1:8000
```

### Regenerate Site Locally (fetches fresh data + rebuilds all pages)
```bash
cd ~/Documents/Claude/"PC Dashboard"
python3 generate_site.py
```

### Fetch FRED Data Only
```bash
cd ~/Documents/Claude/"PC Dashboard"
python3 src/data_fetchers/fred_fetcher.py
```

### Fetch Market Data Only
```bash
cd ~/Documents/Claude/"PC Dashboard"
python3 src/data_fetchers/finance_fetcher.py
```

### Regenerate Chart Pages Only
```bash
cd ~/Documents/Claude/"PC Dashboard"
python3 src/export/generate_chart_pages_v2.py
```

### Export Deal Tracker HTML Only
```bash
cd ~/Documents/Claude/"PC Dashboard"
python3 src/export/export_to_html_v2.py
```

**Note:** These are called automatically by `generate_site.py` and `publish.yml`. Rarely need to run manually.

---

## 📁 Important Locations

| What | Where |
|------|-------|
| Public site files | `github_site/` |
| Homepage | `github_site/index.html` |
| Deal Tracker | `github_site/deals/index.html` |
| Charts | `github_site/charts/*.html` |
| Styles | `github_site/css/style.css` |
| Data Files | `github_site/data/*.json` |
| Database (local replica) | `turso_replica.db` |
| Site Generator | `generate_site.py` |
| Triage App | `src/web/` |
| AI Summarizer | `src/utils/ai_summarizer.py` |
| GitHub Actions | `.github/workflows/` |

---

## 🌐 URLs

| What | URL |
|------|-----|
| Live Site | https://capitalfordefense.com |
| Triage App (Railway) | https://capitalfordefense.up.railway.app |
| Local Test | http://localhost:8080 |
| Local Triage UI | http://127.0.0.1:8000 |
| GitHub Repo | https://github.com/samuelmoyer91-sketch/definvestdashboard |
| FRED API Key | https://fred.stlouisfed.org/docs/api/api_key.html |

---

## 🎨 Customization

### Change Colors
Edit: `github_site/css/style.css`
```css
:root {
  --primary-blue: #1e456e;  /* Navy */
  --accent-green: #88c540;  /* Green */
}
```

### Modify Homepage
Edit: `github_site/index.html`

### Add FRED Series
Edit: `src/data_fetchers/fred_fetcher.py` — add to `FRED_SERIES` dict, then run `generate_site.py`

---

## ⚠️ Troubleshooting

### Charts Not Showing
```bash
# Check data files exist
ls ~/Documents/Claude/"PC Dashboard"/github_site/data/

# Re-generate site
cd ~/Documents/Claude/"PC Dashboard"
python3 generate_site.py
```

### Deal Tracker Empty
```bash
# Re-export deals
cd ~/Documents/Claude/"PC Dashboard"
python3 src/export/export_to_html_v2.py
```

### "FRED API Key Not Set"
```bash
export FRED_API_KEY='your_key_here'
echo $FRED_API_KEY  # verify
```

### Triage Queue Empty (No New Items)
The triage app syncs the Turso replica on every page load. If the queue looks empty despite recent ingest runs:
1. Check GitHub Actions — confirm ingest.yml completed successfully
2. Check for a GitHub issue notification — pipeline failures now create one automatically
3. If ingest succeeded but queue is empty, run the triage app locally to rule out Railway issues:
   ```bash
   cd ~/Documents/Claude/"PC Dashboard"
   uvicorn src.web.app:app --reload
   # Open: http://127.0.0.1:8000
   ```

### Pipeline Failure Notifications
Both `ingest.yml` and `publish.yml` create a GitHub issue if they fail. Check the repo's Issues tab if you suspect something broke. The issue includes a direct link to the failed run's logs.

### Turso Reads Blocked
- If blocked: upgrade plan in Turso dashboard.
- Root cause of spikes: each GitHub Actions runner does a fresh DB sync on startup. Avoid running publish.yml repeatedly in short succession.

### Railway App Down
- Check Railway dashboard — ensure plan is active (paid plan required for 24/7 uptime).
- Or run triage locally: `uvicorn src.web.app:app --reload`

---

## 📚 Documentation

| Doc | What's In It |
|-----|--------------|
| `1 - README.md` | Full project overview, architecture, data sources |
| `docs/AI_WORKFLOW.md` | AI extraction and triage workflow detail |
| `docs/QUICK_REFERENCE.md` | This file |
| `_Session_Logs/` | Per-session change logs |

---

**Keep this file handy for quick command lookup!**
