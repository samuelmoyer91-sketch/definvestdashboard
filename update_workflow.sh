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

case $STAGE in
  "fetch"|"all")
    echo "📥 STAGE 1: Fetching RSS feeds..."
    python3 src/ingest/rss_fetcher.py
    echo "✓ RSS fetch complete"
    echo ""

    if [ "$STAGE" != "all" ]; then exit 0; fi
    ;&

  "scrape")
    echo "🌐 STAGE 2: Scraping article content..."
    python3 src/scraper/article_scraper.py
    echo "✓ Scraping complete"
    echo ""

    if [ "$STAGE" != "all" ]; then exit 0; fi
    ;&

  "ai")
    echo "🤖 STAGE 3: Generating AI summaries..."
    python3 src/scraper/generate_ai_summaries.py --limit 20
    echo "✓ AI summaries complete"
    echo ""

    if [ "$STAGE" != "all" ]; then exit 0; fi

    # Pause for manual triage
    echo "⏸️  MANUAL STEP REQUIRED:"
    echo "   1. Start triage server: cd src/web && uvicorn app:app --reload"
    echo "   2. Open: http://127.0.0.1:8000"
    echo "   3. Review and accept/reject deals"
    echo "   4. When done, run: ./update_workflow.sh publish"
    echo ""
    exit 0
    ;;

  "publish")
    echo "📄 STAGE 4: Publishing website..."
    FRED_API_KEY='skip' python3 publish.py
    echo "✓ Site generated"
    echo ""
    ;&

  "deploy")
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
    ;;

  *)
    echo "Usage: ./update_workflow.sh [stage]"
    echo ""
    echo "Stages:"
    echo "  fetch   - Fetch RSS feeds"
    echo "  scrape  - Scrape article content"
    echo "  ai      - Generate AI summaries"
    echo "  publish - Generate website (after triage)"
    echo "  deploy  - Deploy to GitHub"
    echo "  all     - Run fetch→scrape→ai, then pause for triage"
    echo ""
    echo "Example workflows:"
    echo "  ./update_workflow.sh all      # Fetch data, then pause for triage"
    echo "  ./update_workflow.sh publish  # After triage, publish & deploy"
    exit 1
    ;;
esac
