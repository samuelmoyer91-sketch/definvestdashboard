"""RSS feed ingestion module."""

import feedparser
import json
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import RawItem, get_session


def load_config(config_path='config/feeds.json'):
    """Load RSS feed configuration."""
    with open(config_path, 'r') as f:
        return json.load(f)


def parse_feed(feed_url, feed_name):
    """Parse a single RSS feed and return entries."""
    print(f"Fetching feed: {feed_name}")
    print(f"URL: {feed_url}")

    feed = feedparser.parse(feed_url)

    if feed.bozo:
        print(f"Warning: Feed parsing had issues: {feed.bozo_exception}")

    entries = []
    for entry in feed.entries:
        # Extract relevant fields
        item = {
            'title': entry.get('title', 'No title'),
            'url': entry.get('link', ''),
            'summary': entry.get('summary', ''),
            'published': entry.get('published_parsed', None),
            'feed_source': feed_name
        }

        # Convert published time to datetime
        if item['published']:
            item['published'] = datetime(*item['published'][:6])

        entries.append(item)

    print(f"Found {len(entries)} entries")
    return entries


def save_to_database(entries, session):
    """Save RSS entries to database (skip duplicates)."""
    new_count = 0
    duplicate_count = 0

    for entry in entries:
        # Check if URL already exists
        existing = session.query(RawItem).filter_by(url=entry['url']).first()

        if existing:
            duplicate_count += 1
            continue

        # Create new item
        raw_item = RawItem(
            url=entry['url'],
            title=entry['title'],
            rss_summary=entry['summary'],
            published_date=entry['published'],
            feed_source=entry['feed_source'],
            status='new'
        )

        session.add(raw_item)
        new_count += 1

    session.commit()
    print(f"Saved {new_count} new items, skipped {duplicate_count} duplicates")

    return new_count, duplicate_count


def fetch_all_feeds(config_path='config/feeds.json', db_path='databases/tracker.db'):
    """Fetch all enabled RSS feeds and save to database."""
    print("=" * 60)
    print("Defense Capital Tracker - RSS Ingestion")
    print("=" * 60)
    print()

    # Load configuration
    config = load_config(config_path)

    # Get database session
    session = get_session(db_path)

    total_new = 0
    total_duplicates = 0

    # Fetch each feed
    for feed_config in config['rss_feeds']:
        if not feed_config.get('enabled', True):
            print(f"Skipping disabled feed: {feed_config['name']}")
            continue

        print()
        entries = parse_feed(feed_config['url'], feed_config['name'])
        new, dupes = save_to_database(entries, session)

        total_new += new
        total_duplicates += dupes

    print()
    print("=" * 60)
    print(f"SUMMARY: {total_new} new items, {total_duplicates} duplicates")
    print("=" * 60)

    session.close()

    return total_new, total_duplicates


if __name__ == '__main__':
    # Run from project root
    import os
    os.chdir(Path(__file__).parent.parent.parent)

    fetch_all_feeds()
