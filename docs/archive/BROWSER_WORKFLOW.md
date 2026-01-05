# No Command Line Required - Browser-Only Workflow

**Good news!** You can do everything through your web browser - no command line needed for daily use.

## One-Time Setup (Only Need to Do Once)

### 1. Start the Web Server

Open **Terminal** and run these two commands (copy/paste them):

```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 src/web/app.py
```

Keep this Terminal window open in the background. The server will run until you close it.

**Bookmark this:** http://127.0.0.1:8000

---

## Your Weekly Workflow (All in Browser!)

### Step 1: Fetch New Articles

**Run this in Terminal** (only 2 commands, takes 10 seconds):

```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 src/ingest/rss_fetcher.py && python3 src/scraper/article_scraper.py 10
```

This fetches RSS feeds and scrapes 10 articles. You'll see output like:
```
Found 8 new items
Scraped 6 articles successfully
```

### Step 2: Triage Items (In Browser)

1. **Open:** http://127.0.0.1:8000 in your browser
2. You'll see a list of articles to review
3. **Click "Review & Accept"** on relevant items
4. Fill out the form:
   - Company name
   - Investment amount
   - Capital type (dropdown)
   - Sector, Location, etc.
   - Summary
5. **Click "Accept & Add to Master List"**
6. Repeat for other relevant articles
7. **Click "Reject"** on irrelevant items

### Step 3: Export to CSV (In Browser)

1. **Click "Master List"** in the navigation menu
2. You'll see all your curated deals in a table
3. **Click the "📥 Export to CSV" button** (top right)
4. Your browser will download: `defense_capital_deals.csv`
5. The file goes to your **Downloads** folder

### Step 4: Upload to Google Sheets

1. Go to your Google Sheet (or create a new one)
2. **File → Import**
3. **Upload** tab
4. Select `defense_capital_deals.csv` from your Downloads folder
5. Import location: **"Replace current sheet"**
6. **Click "Import data"**
7. Done! Your Google Site auto-updates

---

## Simplified Weekly Routine

**Monday morning (15 minutes total):**

1. **Terminal** (2 commands, 30 seconds):
   ```bash
   cd ~/Documents/"Claude - Defense PC Dashboard"
   python3 src/ingest/rss_fetcher.py && python3 src/scraper/article_scraper.py 10
   ```

2. **Browser** - Triage Queue (10 minutes):
   - Go to http://127.0.0.1:8000
   - Review 5-10 articles
   - Accept relevant ones, reject irrelevant

3. **Browser** - Export (30 seconds):
   - Click "Master List"
   - Click "📥 Export to CSV"
   - File downloads automatically

4. **Google Sheets** (2 minutes):
   - File → Import → Upload CSV
   - Replace current sheet
   - Done!

**That's it!** Your Google Site updates automatically.

---

## What Each Page Does

### Triage Queue (http://127.0.0.1:8000)
- Shows articles that need review
- Accept relevant items
- Reject irrelevant items

### Master List (http://127.0.0.1:8000/master)
- Shows all accepted items
- **Export to CSV button** here
- This is your publication-ready data

### Statistics (http://127.0.0.1:8000/stats)
- Total items tracked
- Items by feed source
- Quick overview

---

## Bookmarks to Save

Save these in your browser:

- **Triage Queue:** http://127.0.0.1:8000
- **Master List:** http://127.0.0.1:8000/master
- **Statistics:** http://127.0.0.1:8000/stats

---

## Tips for Non-Technical Users

### Starting the Server Daily

If you close Terminal or restart your computer, you'll need to start the server again:

```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 src/web/app.py
```

**Pro tip:** Keep Terminal open in the background and just minimize it.

### If You See "Connection Refused"

It means the server isn't running. Start it with:
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 src/web/app.py
```

### Where Did My CSV Go?

Check your **Downloads** folder. The file is named: `defense_capital_deals.csv`

### How Often Should I Run This?

**Recommendation:** Once a week is perfect for this type of data.

Defense private capital announcements aren't time-sensitive - weekly updates are fine.

---

## The Two Terminal Commands You Need

**Command 1: Fetch & Scrape** (Run weekly)
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 src/ingest/rss_fetcher.py && python3 src/scraper/article_scraper.py 10
```

**Command 2: Start Web Server** (Run once, keep open)
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 src/web/app.py
```

Everything else is in the browser!

---

## Future: Even Simpler

If you want **zero Terminal commands**, I can:
1. Create a Mac app icon you double-click
2. Set up automatic RSS fetching (runs daily in background)
3. Build a desktop app (no browser needed)

But for now, this workflow is simple enough: 2 terminal commands, everything else in browser.

Let me know if you want any of those improvements!
