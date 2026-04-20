"""RSS feed ingestion module."""

import feedparser
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import RawItem, get_session
from src.utils.relevance_scorer import calculate_relevance_score, should_auto_reject


PROJECT_ROOT = Path(__file__).parent.parent.parent


def load_config(config_path='config/feeds.json'):
    """Load RSS feed configuration."""
    path = Path(config_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    with open(path, 'r') as f:
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


MAX_AGE_DAYS = 365


def save_to_database(entries, session, config=None):
    """Save RSS entries to database with relevance scoring (skip duplicates)."""
    new_count = 0
    duplicate_count = 0
    auto_rejected_count = 0
    stale_count = 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)

    for entry in entries:
        # Skip items older than MAX_AGE_DAYS (but pass through items with no date)
        pub = entry.get('published')
        if pub is not None:
            pub_aware = pub.replace(tzinfo=timezone.utc) if pub.tzinfo is None else pub
            if pub_aware < cutoff:
                stale_count += 1
                continue

        # Skip YouTube links (video duplicates of news articles, not useful for triage)
        if 'youtube.com' in entry.get('url', '') or 'youtu.be' in entry.get('url', ''):
            continue

        # Check if URL already exists
        existing = session.query(RawItem).filter_by(url=entry['url']).first()

        if existing:
            duplicate_count += 1
            continue

        # Calculate relevance score
        score, matched_keywords, exclude_matched = calculate_relevance_score(
            entry['title'],
            entry['summary'],
            config
        )

        # Check if should auto-reject
        reject, reject_reason = should_auto_reject(score, matched_keywords, exclude_matched)

        if reject:
            status = 'auto_rejected'
            auto_rejected_count += 1
            print(f"  ⊘ Auto-rejected: {entry['title'][:50]}...")
            print(f"    Reason: {reject_reason}")
        else:
            status = 'new'

        # Create new item with relevance data
        raw_item = RawItem(
            url=entry['url'],
            title=entry['title'],
            rss_summary=entry['summary'],
            published_date=entry['published'],
            feed_source=entry['feed_source'],
            status=status,
            relevance_score=score,
            relevance_flags=','.join(matched_keywords) if matched_keywords else None
        )

        session.add(raw_item)
        new_count += 1

    session.commit()
    print(f"Saved {new_count} new items ({auto_rejected_count} auto-rejected), skipped {duplicate_count} duplicates, {stale_count} stale (>{MAX_AGE_DAYS}d)")

    return new_count, duplicate_count, auto_rejected_count, stale_count


def fetch_all_feeds(config_path='config/feeds.json', db_path='databases/tracker.db'):
    """Fetch all enabled RSS feeds and save to database with relevance filtering."""
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
    total_auto_rejected = 0
    total_stale = 0

    # Fetch each feed
    for feed_config in config['rss_feeds']:
        if not feed_config.get('enabled', True):
            print(f"Skipping disabled feed: {feed_config['name']}")
            continue

        print()
        entries = parse_feed(feed_config['url'], feed_config['name'])
        new, dupes, rejected, stale = save_to_database(entries, session, config)

        total_new += new
        total_duplicates += dupes
        total_auto_rejected += rejected
        total_stale += stale

    print()
    print("=" * 60)
    print(f"SUMMARY: {total_new} new items ({total_auto_rejected} auto-rejected), {total_duplicates} duplicates, {total_stale} stale (>{MAX_AGE_DAYS}d)")
    print("=" * 60)

    session.close()

    return total_new, total_duplicates, total_auto_rejected, total_stale


if __name__ == '__main__':
    # Run from project root
    import os
    os.chdir(Path(__file__).parent.parent.parent)

    fetch_all_feeds()
