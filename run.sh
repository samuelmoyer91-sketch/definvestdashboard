#!/bin/bash
# Defense Capital Tracker - Quick Start Script

echo "==================================="
echo "Defense Capital Tracker"
echo "==================================="
echo ""

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Function to show menu
show_menu() {
    echo "Choose an option:"
    echo "  1) Fetch new RSS feeds"
    echo "  2) Scrape articles (all pending)"
    echo "  3) Scrape articles (10 at a time)"
    echo "  4) Start web interface"
    echo "  5) Export master list to CSV"
    echo "  6) View stats"
    echo "  7) Exit"
    echo ""
    read -p "Enter choice [1-7]: " choice
    echo ""
}

# Main loop
while true; do
    show_menu

    case $choice in
        1)
            echo "Fetching RSS feeds..."
            python3 src/ingest/rss_fetcher.py
            echo ""
            read -p "Press Enter to continue..."
            ;;
        2)
            echo "Scraping all pending articles..."
            python3 src/scraper/article_scraper.py
            echo ""
            read -p "Press Enter to continue..."
            ;;
        3)
            echo "Scraping 10 articles..."
            python3 src/scraper/article_scraper.py 10
            echo ""
            read -p "Press Enter to continue..."
            ;;
        4)
            echo "Starting web interface..."
            echo "Open your browser to: http://127.0.0.1:8000"
            echo "Press Ctrl+C to stop the server"
            echo ""
            python3 src/web/app.py
            ;;
        5)
            echo "Exporting master list to CSV..."
            python3 src/export/export_to_csv.py
            echo ""
            echo "File location: exports/master_list.csv"
            echo ""
            read -p "Press Enter to continue..."
            ;;
        6)
            python3 src/utils/view_data.py stats
            echo ""
            read -p "Press Enter to continue..."
            ;;
        7)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo "Invalid choice. Please try again."
            sleep 2
            ;;
    esac
    echo ""
done
