# GitHub Pages Setup Guide

**Your Defense Capital Dashboard is ready to deploy!**

This guide walks you through getting your dashboard live on GitHub Pages.

---

## Overview

Your dashboard combines:
- **Deal Tracker**: Private capital investments in defense sector (from your RSS feeds)
- **Economic Charts**: 10 FRED indicators showing defense spending and industrial health
- **Market Data**: Defense ETFs (ITA, XLI), Prologis, and Treasury yields

**Site Location**: `~/Documents/Claude - Defense PC Dashboard/github_site/`

---

## Quick Start (5 minutes)

### 1. Get a FRED API Key (Free)

You need this to fetch economic data:

1. Visit: https://fred.stlouisfed.org/docs/api/api_key.html
2. Click "Request API Key"
3. Sign in with your email (or create account)
4. Copy your API key

**Set it in your terminal:**
```bash
export FRED_API_KEY='your_actual_api_key_here'
```

To make it permanent, add to your `~/.zshrc` (or `~/.bash_profile`):
```bash
echo "export FRED_API_KEY='your_actual_api_key_here'" >> ~/.zshrc
source ~/.zshrc
```

### 2. Generate Your Site

Run the publish script to fetch all data and build the site:

```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 publish.py
```

This will:
- ✓ Fetch 10 FRED economic series
- ✓ Fetch stock/ETF data (ITA, XLI, PLD)
- ✓ Generate 15 chart pages
- ✓ Export your deal tracker to HTML

### 3. Test Locally

Preview your site before publishing:

```bash
cd ~/Documents/"Claude - Defense PC Dashboard"/github_site
python3 -m http.server 8080
```

Then open in your browser: **http://localhost:8080**

Press `Ctrl+C` to stop the server when done.

### 4. Create GitHub Repository

**IMPORTANT: Create a PRIVATE repository first!**

1. Go to: https://github.com/new
2. Repository name: `defense-dashboard`
3. Description: "Defense sector investment and economic data dashboard"
4. **Select: Private** (you can make it public later)
5. Do NOT initialize with README
6. Click "Create repository"

### 5. Push Your Site to GitHub

```bash
cd ~/Documents/"Claude - Defense PC Dashboard"/github_site

# Initialize git
git init
git add .
git commit -m "Initial commit: Defense Capital Dashboard"

# Connect to GitHub (replace with your actual repo URL)
git branch -M main
git remote add origin https://github.com/samuelmoyer91-sketch/defense-dashboard.git
git push -u origin main
```

### 6. Enable GitHub Pages

1. Go to your repo: https://github.com/samuelmoyer91-sketch/defense-dashboard
2. Click **Settings** (top right)
3. Scroll down to **Pages** (left sidebar)
4. Under "Source":
   - Branch: `main`
   - Folder: `/ (root)`
5. Click **Save**

**Wait 1-2 minutes**, then your site will be live at:
**https://samuelmoyer91-sketch.github.io/defense-dashboard/**

---

## Updating Your Dashboard

### Update Deal Tracker

1. Fetch new RSS articles:
   ```bash
   cd ~/Documents/"Claude - Defense PC Dashboard"
   python3 src/ingest/rss_fetcher.py
   python3 src/scraper/article_scraper.py 10
   ```

2. Review articles in browser:
   ```bash
   python3 src/web/app.py
   # Open: http://127.0.0.1:8000
   ```

3. Rebuild and publish:
   ```bash
   python3 publish.py
   cd github_site
   git add .
   git commit -m "Update deal tracker"
   git push
   ```

### Update Economic/Market Data

Just run the publish script:

```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 publish.py
cd github_site
git add .
git commit -m "Update data"
git push
```

### Update Schedule Recommendations

- **Deal Tracker**: Weekly (to review new articles)
- **Economic Data**: Weekly or monthly (FRED updates monthly)
- **Market Data**: Daily if you want current prices

---

## File Structure

```
github_site/
├── index.html                 # Homepage
├── deals/
│   └── index.html            # Deal tracker (searchable table)
├── charts/
│   ├── defense-spending.html # 10 FRED charts
│   ├── market-overview.html  # Market comparison
│   └── ... (15 total charts)
├── css/
│   └── style.css            # Teal theme (#226E93)
├── js/
│   └── main.js              # Chart.js utilities
└── data/
    ├── fdefx.json           # FRED data files
    ├── ita.json             # Stock/ETF data
    └── ... (14 JSON files)
```

---

## Customization

### Change Colors

Edit `github_site/css/style.css`:

```css
:root {
  --primary-teal: #226E93;     /* Change to your color */
  --accent-teal: #88c0d0;      /* Lighter accent */
}
```

### Add More Charts

1. Add series to `src/data_fetchers/fred_fetcher.py`
2. Add chart definition to `src/export/generate_chart_pages.py`
3. Run `python3 publish.py`

### Modify Homepage

Edit `github_site/index.html` directly.

---

## Making Your Site Public

When you're ready to share:

1. Go to repo Settings
2. Scroll to "Danger Zone"
3. Click "Change repository visibility"
4. Select "Public"

**Remember**: Your deal tracker will be visible. Review it first!

---

## Automation (Future)

You can set up GitHub Actions to auto-update data:

1. Create `.github/workflows/update-data.yml`
2. Schedule daily/weekly runs
3. Store FRED_API_KEY as GitHub Secret
4. Auto-commit updated data

*(Let me know if you want help setting this up!)*

---

## Troubleshooting

### Charts not showing?

- Make sure you ran `python3 publish.py` with FRED API key set
- Check that `github_site/data/` has JSON files
- Open browser console (F12) for errors

### Deal tracker empty?

- You need to add deals to the master list first
- Run the triage workflow: `python3 src/web/app.py`
- Accept some articles, then run `python3 publish.py`

### GitHub Pages 404 error?

- Wait 2-3 minutes after enabling Pages
- Verify repo is public (or you're logged into GitHub)
- Check Settings > Pages shows the URL

### Data fetch fails?

- Verify FRED API key: `echo $FRED_API_KEY`
- Check network connection
- Some FRED series may be renamed - update IDs if needed

---

## Support

- FRED API Docs: https://fred.stlouisfed.org/docs/api/
- GitHub Pages Docs: https://docs.github.com/en/pages
- Chart.js Docs: https://www.chartjs.org/docs/

---

## What's Next?

**Phase 3 Ideas:**
- AI-powered deal extraction (using Anthropic API)
- Email alerts for high-value deals
- Map view of investments by location
- RSS feed of your deals
- Custom domain (e.g., defensecapital.com)
- Automated daily updates via GitHub Actions

---

**You're all set! Your dashboard is ready to impress.** 🚀

Run `python3 publish.py` to get started!
