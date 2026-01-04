# How to Export CSV (Browser Button)

## Where to Find the Export Button

1. **Open your browser** to: http://127.0.0.1:8000
2. **Click "Master List"** in the navigation menu (top of page)
3. Look for the **"📥 Export to CSV"** button in the top-right corner
4. **Click it** - your browser will download the file automatically

## What Happens When You Click

```
┌─────────────────────────────────────────────────┐
│  Defense Private Capital Intelligence Platform  │
│  [Triage Queue] [Master List] [Statistics]      │
└─────────────────────────────────────────────────┘

Master List (23 items)         [📥 Export to CSV] ← CLICK HERE

┌──────────────────────────────────────────────────┐
│ Company          Investment    Type    Sector    │
├──────────────────────────────────────────────────┤
│ McNally Capital  Undisclosed   PE     Aerospace  │
│ Anduril          $1.5B         VC     Drones     │
│ ...                                               │
└──────────────────────────────────────────────────┘
```

When you click, your browser downloads: `defense_capital_deals.csv`

## Where the File Goes

**Mac:** `~/Downloads/defense_capital_deals.csv`

Your browser's download bar (bottom of window) will show the file.

## What to Do With the CSV

### Option A: Upload to Google Sheets

1. Open your Google Sheet
2. **File → Import**
3. **Upload** tab
4. Select `defense_capital_deals.csv` from Downloads
5. Import location: **"Replace current sheet"**
6. **Import data**

### Option B: Open in Excel/Numbers

Just double-click the CSV file in your Downloads folder.

## When to Export

**After you've curated new items:**
1. Triage some articles (accept 5-10 items)
2. Go to Master List
3. Click Export
4. Upload to Google Sheets

**How often:** Weekly is fine.

## Troubleshooting

**Button is grayed out or missing?**
- You need at least 1 item in your master list
- Go to Triage Queue and accept an item first

**Download didn't start?**
- Check your browser's download settings
- Some browsers block automatic downloads
- Look for a permission prompt

**File is empty or has weird characters?**
- This shouldn't happen, but if it does, let me know

## No Command Line!

The old way (command line):
```bash
cd ~/Documents/"Claude - Defense PC Dashboard"
python3 src/export/export_to_csv.py
```

The new way (browser):
- Click "Master List"
- Click "📥 Export to CSV"
- Done!

Much easier!
