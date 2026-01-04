"""Inspect a scraped article."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import RawItem, ArticleContent, get_session


def inspect_article(item_id):
    """Show details of a scraped article."""
    session = get_session()

    raw_item = session.query(RawItem).filter_by(id=item_id).first()
    if not raw_item:
        print(f"No item found with ID {item_id}")
        return

    article = session.query(ArticleContent).filter_by(item_id=item_id).first()

    print("=" * 80)
    print(f"ARTICLE INSPECTION - ID: {item_id}")
    print("=" * 80)
    print()

    print(f"Title: {raw_item.title}")
    print(f"URL: {raw_item.url}")
    print(f"Feed: {raw_item.feed_source}")
    print(f"Published: {raw_item.published_date}")
    print(f"Status: {raw_item.status}")
    print()

    if article:
        print(f"Scraped: {article.scraped_at}")
        print(f"Success: {article.scrape_success}")

        if article.scrape_success:
            print(f"Text length: {len(article.clean_text) if article.clean_text else 0} chars")
            print()
            print("First 500 chars of text:")
            print("-" * 80)
            if article.clean_text:
                print(article.clean_text[:500])
            else:
                print("(No text content)")
        else:
            print(f"Error: {article.error_message}")
    else:
        print("Not yet scraped")

    session.close()


if __name__ == '__main__':
    import os
    os.chdir(Path(__file__).parent.parent.parent)

    if len(sys.argv) < 2:
        print("Usage: python inspect_article.py <item_id>")
        print("\nAvailable items:")

        session = get_session()
        items = session.query(RawItem).limit(10).all()
        for item in items:
            status = "✓" if item.status == 'scraped' else "○"
            print(f"  {status} ID {item.id}: {item.title[:60]}")
        session.close()
    else:
        inspect_article(int(sys.argv[1]))
