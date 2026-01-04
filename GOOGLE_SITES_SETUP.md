# Adding Your Deal Tracker to Google Sites

## Step-by-Step Instructions

### 1. Export Your Master List to CSV

```bash
cd ~/Documents/"Claude - Defense PC Dashboard"

# Option A: Use the menu
./run.sh
# Choose option 5: Export master list to CSV

# Option B: Run directly
python3 src/export/export_to_csv.py
```

This creates: `exports/master_list.csv`

### 2. Import CSV to Google Sheets

1. Go to https://sheets.google.com
2. Click **"Blank"** to create a new spreadsheet
3. **File → Import**
4. **Upload** tab
5. Click **"Select a file from your device"**
6. Choose `master_list.csv` from your exports folder
7. Import location: **"Replace spreadsheet"**
8. Click **"Import data"**
9. Rename the sheet: **"Defense Private Investment Deals"** (or similar)

### 3. Format the Google Sheet (Optional but Recommended)

To match your other dashboards:

1. **Header row (Row 1):**
   - Select row 1
   - **Format → Text → Bold**
   - **Fill color:** Choose your site's header color (teal)
   - **Text color:** White

2. **Freeze header:**
   - **View → Freeze → 1 row**

3. **Column widths:**
   - Date: Narrow (~100px)
   - Company: Medium (~150px)
   - Investment Amount: Medium (~120px)
   - Summary: Wide (~300px)
   - Source URL: You can hide this or make it narrow

4. **Make URLs clickable:**
   - Select the "Source URL" column
   - Right-click → **"Insert link"** or Ctrl+K
   - Or just keep as text (users can copy/paste)

5. **Share settings:**
   - Click **"Share"** (top right)
   - Change to **"Anyone with the link can view"**
   - Copy the share link

### 4. Add to Your Google Site

Following the pattern from your existing pages:

1. Go to your Google Site editor: https://sites.google.com/view/defense-capital-dashboard
2. **Click "Pages"** (left sidebar)
3. Choose where to add the new page:
   - **Option A:** Add under "Defense Investment Trends" section
   - **Option B:** Create a new top-level section called "Private Investment Deals"

4. **Add the page:**
   - Click the **"+"** button next to your chosen section
   - Name it: **"Private Investment Deals"** or **"Deal Tracker"**

5. **Add the embedded sheet:**
   - On your new page, click **"Insert"**
   - Choose **"Embed"**
   - Paste your Google Sheets share URL
   - Click **"Insert"**

6. **Add context text** (optional):
   - Above the embedded sheet, add a text box
   - Example text:
     ```
     Private Investment Deals in Defense & Dual-Use

     This tracker monitors announced private capital investments (VC, PE,
     corporate) in U.S. defense manufacturing, dual-use technology, and
     defense-adjacent infrastructure. Data is curated from industry news
     and press releases.

     Last Updated: [Date]
     ```

7. **Publish:**
   - Click **"Publish"** (top right)
   - Confirm

### 5. Your Weekly Update Workflow

Once set up, updating is simple:

```bash
# 1. Fetch new RSS items
python3 src/ingest/rss_fetcher.py

# 2. Scrape articles
python3 src/scraper/article_scraper.py 10

# 3. Open web UI and triage
python3 src/web/app.py
# Go to http://127.0.0.1:8000
# Accept relevant items

# 4. Export to CSV
python3 src/export/export_to_csv.py

# 5. Update Google Sheet
# - Open your Google Sheet
# - File → Import → Upload
# - Choose exports/master_list.csv
# - Import location: "Replace current sheet"
# - Done! Your Google Site auto-updates
```

**Frequency:** Weekly or bi-weekly is fine for this type of data.

## Alternative: Direct Google Sheets API (Advanced)

If you want **automatic updates** without manual CSV uploads, I can build a script that:
- Uses Google Sheets API
- Authenticates with your Google account
- Directly updates the sheet from Python

**Pros:** Fully automated (run one command, sheet updates)
**Cons:** Requires OAuth setup (~15 minutes of config)

Let me know if you want this!

## Page Layout Recommendations

To match your existing site style:

### Suggested Page Title
**"Private Investment Deals"**

### Suggested Navigation Position
Add under **"Defense Investment Trends"** as:
- Defense Capital Goods Production
- Defense VC Activity
- Defense M&A Activity
- **→ Private Investment Deals** ← NEW

OR create a new top-level section:
- Defense Investment Trends
- Defense Industrial Health
- Overall US Industrial Health
- **→ Private Capital Deal Tracker** ← NEW SECTION

### Table Display Options

**Option 1: Full embed** (like your other charts)
- Shows entire table
- Users can scroll/sort within the iframe
- Matches your current style

**Option 2: Filtered view**
- Create 2-3 separate sheets in the same file:
  - "All Deals" (complete list)
  - "Recent Deals" (last 6 months)
  - "Major Deals" (>$100M only)
- Embed different sheets on different pages

## Example: What It Will Look Like

```
┌─────────────────────────────────────────────────┐
│  Defense Private Capital Dashboard              │
│  [Your Navigation Menu]                         │
└─────────────────────────────────────────────────┘

Private Investment Deals
────────────────────────────────────────────────

This tracker monitors announced private capital
investments in U.S. defense and dual-use sectors.

[Embedded Google Sheet - scrollable table showing:]

Date       | Company         | Investment  | Type | Sector
──────────────────────────────────────────────────────────
2026-01-02 | McNally Capital| Undisclosed | PE   | Aerospace
2026-01-05 | Anduril        | $1.5B       | VC   | Drones
...
```

## Troubleshooting

**Sheet not showing on site:**
- Make sure sharing is set to "Anyone with link can view"
- Try using the "Publish to web" link instead (File → Share → Publish to web)

**Data looks messy:**
- Format the header row (bold, colored background)
- Adjust column widths
- Consider hiding the "Source URL" column

**Want to show charts too:**
- In Google Sheets, create a pivot table or chart
- Embed the chart on your site (like your other pages)
- Example: "Deals by Sector" pie chart, "Investment by Quarter" bar chart

## Next Steps

Once you have 20-30 deals in your master list, consider adding:
1. **Summary stats** (total capital tracked, number of deals)
2. **Charts** (deals over time, breakdown by sector)
3. **Filters** (by year, sector, capital type)

Let me know if you need help with any of these steps!
