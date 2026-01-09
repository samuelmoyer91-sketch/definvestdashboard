# Quick Reference Card

**Defense Capital Dashboard - Commands You'll Use**

---

## ⭐ Primary Workflow (Use This)

### Complete Weekly Update
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"

# 1. Fetch new deals and generate AI summaries
./update_workflow.sh all

# 2. Review deals in triage UI
uvicorn src.web.app:app --reload
# Open http://127.0.0.1:8000
# Accept/reject deals with collapsible cards

# 3. Publish everything (auto-deploys)
./update_workflow.sh publish
```

**Done!** Site updates in ~30 seconds at https://samuelmoyer91-sketch.github.io/definvestdashboard/

---

## 🚀 Initial Setup (Do Once)

### 1. Get FRED API Key
```bash
# Visit: https://fred.stlouisfed.org/docs/api/api_key.html
# Then set it:
export FRED_API_KEY='your_key_here'

# Make permanent:
echo "export FRED_API_KEY='your_key_here'" >> ~/.zshrc
```

### 2. Generate Site
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 generate_site.py
```

### 3. Test Locally
```bash
cd github_site
python3 -m http.server 8080
# Open: http://localhost:8080
```

### 4. Deploy to GitHub
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"/github_site

# First time
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/samuelmoyer91-sketch/defense-dashboard.git
git push -u origin main

# Enable Pages in repo Settings > Pages
```

---

## 📊 Alternative Workflows

### Manual Update (Advanced - If Workflow Script Fails)

**Update Deal Tracker + Data:**
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"

# 1. Fetch new articles
python3 src/ingest/rss_fetcher.py
python3 src/scraper/article_scraper.py
python3 src/scraper/generate_ai_summaries.py

# 2. Review in triage UI
uvicorn src.web.app:app --reload
# Open: http://127.0.0.1:8000
# Accept/reject articles

# 3. Generate site
python3 generate_site.py

# 4. Deploy manually
git add github_site/
git commit -m "Weekly update"
git push origin main
git subtree push --prefix github_site origin gh-pages
```

**Update Data Only (No New Deals):**
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 generate_site.py
git add github_site/
git commit -m "Data refresh"
git push origin main
git subtree push --prefix github_site origin gh-pages
```

---

## 🔧 Common Tasks

### Test Site Locally
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"/github_site
python3 -m http.server 8080
# Open: http://localhost:8080
# Press Ctrl+C to stop
```

### Fetch FRED Data Only
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 src/data_fetchers/fred_fetcher.py
```

### Fetch Market Data Only
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 src/data_fetchers/finance_fetcher.py
```

### Regenerate Chart Pages
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 src/export/generate_chart_pages_v2.py
```

### Export Deal Tracker HTML
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 src/export/export_to_html_v2.py
```

**Note:** These are called automatically by `generate_site.py`, rarely need to run manually.

---

## 📁 Important Locations

| What | Where |
|------|-------|
| GitHub Pages Site | `~/Documents/Claude - Defense PC Dashboard/github_site/` |
| Homepage | `github_site/index.html` |
| Deal Tracker | `github_site/deals/index.html` |
| Charts | `github_site/charts/*.html` |
| Styles | `github_site/css/style.css` |
| Data Files | `github_site/data/*.json` |
| Database | `data/tracker.db` |
| Site Generator | `generate_site.py` |

---

## 🌐 URLs

| What | URL |
|------|-----|
| Local Test | http://localhost:8080 |
| Triage UI | http://127.0.0.1:8000 |
| Live Site | https://samuelmoyer91-sketch.github.io/defense-dashboard/ |
| GitHub Repo | https://github.com/samuelmoyer91-sketch/defense-dashboard |
| FRED API Key | https://fred.stlouisfed.org/docs/api/api_key.html |

---

## 📋 Checklist: Before Going Public

- [ ] Test locally (http://localhost:8080)
- [ ] All charts load correctly
- [ ] Deal tracker shows deals properly
- [ ] Search/filter works
- [ ] Mobile view looks good
- [ ] No sensitive info visible
- [ ] Footer attribution correct
- [ ] Links work in navigation
- [ ] Review GitHub repo is PRIVATE
- [ ] Ready to share? Change repo to PUBLIC

---

## 🎨 Customization

### Change Colors
Edit: `github_site/css/style.css`
```css
:root {
  --primary-teal: #226E93;  /* Main color */
  --accent-teal: #88c0d0;   /* Accent */
}
```

### Modify Homepage
Edit: `github_site/index.html`

### Add FRED Series
Edit: `src/data_fetchers/fred_fetcher.py`
Add to `FRED_SERIES` dict, then run `publish.py`

---

## ⚠️ Troubleshooting

### Charts Not Showing
```bash
# Check data files exist
ls ~/Documents/"Claude - Defense PC Dashboard"/github_site/data/

# Re-fetch data
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 publish.py
```

### Deal Tracker Empty
```bash
# Check database has deals
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 src/utils/view_data.py

# Re-export
python3 src/export/export_to_html.py
```

### "FRED API Key Not Set"
```bash
# Set API key
export FRED_API_KEY='your_key_here'

# Verify it's set
echo $FRED_API_KEY
```

### GitHub Push Fails
```bash
# Check remote is set
cd github_site
git remote -v

# If not set:
git remote add origin https://github.com/samuelmoyer91-sketch/defense-dashboard.git
```

---

## 📚 Documentation

| Doc | What's In It |
|-----|--------------|
| NIGHT_BUILD_SUMMARY.md | Everything built tonight |
| GITHUB_PAGES_SETUP.md | Detailed deployment guide |
| QUICK_REFERENCE.md | This file (commands) |
| PROJECT_HANDOFF.md | Original project spec |

---

## 🎯 Quick Win: 5-Minute Deploy

```bash
# 1. Set API key
export FRED_API_KEY='your_key_here'

# 2. Generate
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 generate_site.py

# 3. Test
cd github_site
python3 -m http.server 8080
# Open browser, verify looks good, Ctrl+C

# 4. Deploy
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/samuelmoyer91-sketch/defense-dashboard.git
git push -u origin main

# 5. Enable Pages (via GitHub website)
# Done! 🎉
```

---

**Keep this file handy for quick command lookup!**
