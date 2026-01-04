"""RSS ingestion package."""

from .rss_fetcher import fetch_all_feeds, parse_feed

__all__ = ['fetch_all_feeds', 'parse_feed']
