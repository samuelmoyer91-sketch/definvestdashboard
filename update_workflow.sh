#!/bin/bash
# Complete workflow: Fetch → Scrape → AI → Triage → Publish → Deploy
# Run this script in stages, with manual triage in between

set -e  # Exit on error

cd ~/Documents/"Claude - Defense PC Dashboard"

echo "============================================"
echo "Defense Dashboard - Complete Update Workflow"
echo "============================================"
echo ""

# Check which stage to run
STAGE=${1:-all}

if [ "$STAGE" = "all" ]; then
  # Run fetch → scrape → ai, then pause
  echo "📥 STAGE 1: Fetching RSS feeds..."
  python3 src/ingest/rss_fetcher.py
  echo "✓ RSS fetch complete"
  echo ""

  echo "🌐 STAGE 2: Scraping article content..."
  python3 src/scraper/article_scraper.py
  echo "✓ Scraping complete"
  echo ""

  echo "🤖 STAGE 3: Generating AI summaries..."
  python3 src/scraper/generate_ai_summaries.py --limit 20
  echo "✓ AI summaries complete"
  echo ""

  # Pause for manual triage
  echo "⏸️  MANUAL STEP REQUIRED:"
  echo "   1. Start triage server:"
  echo "      uvicorn src.web.app:app --reload"
  echo "   2. Open: http://127.0.0.1:8000"
  echo "   3. Review and accept/reject deals"
  echo "   4. When done, run: ./update_workflow.sh publish"
  echo ""
  exit 0

elif [ "$STAGE" = "fetch" ]; then
  echo "📥 STAGE 1: Fetching RSS feeds..."
  python3 src/ingest/rss_fetcher.py
  echo "✓ RSS fetch complete"

elif [ "$STAGE" = "scrape" ]; then
  echo "🌐 STAGE 2: Scraping article content..."
  python3 src/scraper/article_scraper.py
  echo "✓ Scraping complete"

elif [ "$STAGE" = "ai" ]; then
  echo "🤖 STAGE 3: Generating AI summaries..."
  python3 src/scraper/generate_ai_summaries.py --limit 20
  echo "✓ AI summaries complete"

elif [ "$STAGE" = "publish" ]; then
  # Publish and automatically deploy
  echo "📄 STAGE 4: Refreshing economic data & publishing website..."
  echo "   - Fetching FRED economic indicators..."
  echo "   - Fetching Yahoo Finance market data..."
  echo "   - Generating chart pages..."
  echo "   - Exporting deal tracker..."
  echo ""
  python3 publish.py
  echo "✓ Site generated with fresh data"
  echo ""

  # Automatically proceed to deploy
  echo "🚀 STAGE 5: Deploying to GitHub..."

  # Check if there are changes
  if git diff --quiet github_site/; then
    echo "⚠️  No changes detected in github_site/"
    echo "   Did you accept any deals in triage?"
    exit 0
  fi

  # Commit and push
  git add github_site/
  git commit -m "Update deals - $(date +%Y-%m-%d)"
  git push origin main

  # Deploy to GitHub Pages
  echo ""
  echo "📤 Deploying to GitHub Pages..."
  git subtree push --prefix github_site origin gh-pages

  echo ""
  echo "✅ DEPLOYMENT COMPLETE!"
  echo "   Your site will update in ~30 seconds at:"
  echo "   https://samuelmoyer91-sketch.github.io/definvestdashboard/"

elif [ "$STAGE" = "deploy" ]; then
  echo "🚀 STAGE 5: Deploying to GitHub..."

  # Check if there are changes
  if git diff --quiet github_site/; then
    echo "⚠️  No changes detected in github_site/"
    echo "   Did you accept any deals in triage?"
    exit 0
  fi

  # Commit and push
  git add github_site/
  git commit -m "Update deals - $(date +%Y-%m-%d)"
  git push origin main

  # Deploy to GitHub Pages
  echo ""
  echo "📤 Deploying to GitHub Pages..."
  git subtree push --prefix github_site origin gh-pages

  echo ""
  echo "✅ DEPLOYMENT COMPLETE!"
  echo "   Your site will update in ~30 seconds at:"
  echo "   https://samuelmoyer91-sketch.github.io/definvestdashboard/"

else
  echo "Usage: ./update_workflow.sh [stage]"
  echo ""
  echo "Stages:"
  echo "  fetch   - Fetch RSS feeds (deal articles)"
  echo "  scrape  - Scrape article content"
  echo "  ai      - Generate AI summaries for deals"
  echo "  publish - Refresh ALL data (FRED, Yahoo Finance, deals) & generate site + deploy"
  echo "  deploy  - Deploy to GitHub Pages only"
  echo "  all     - Run fetch→scrape→ai, then pause for triage"
  echo ""
  echo "Complete workflow:"
  echo "  1. ./update_workflow.sh all      # Fetch deal data, pause for triage"
  echo "  2. [Do manual triage at http://127.0.0.1:8000]"
  echo "  3. ./update_workflow.sh publish  # Refresh economic data + publish + deploy"
  echo ""
  echo "Note: 'publish' stage fetches fresh FRED & Yahoo Finance data automatically"
  exit 1
fi
