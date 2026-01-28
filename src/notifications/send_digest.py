"""Send digest email with pending items ready for triage.

Queries items that:
1. Have been successfully scraped
2. Have AI summaries
3. Are not yet in master list or rejected

This script is called by GitHub Actions after RSS processing completes.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database import RawItem, ArticleContent, AIExtraction, MasterItem, RejectedItem, get_session
from src.notifications.email_sender import DigestItem, send_digest_email


def get_pending_items(limit: int = 20) -> list:
    """Query pending items with AI summaries ready for triage.

    Args:
        limit: Maximum number of items to include in digest

    Returns:
        List of DigestItem objects
    """
    session = get_session()

    try:
        # Get items that:
        # 1. Have been successfully scraped
        # 2. Have AI extraction
        # 3. Are not in master list
        # 4. Are not rejected
        items = session.query(RawItem).join(
            ArticleContent, RawItem.id == ArticleContent.item_id
        ).join(
            AIExtraction, RawItem.id == AIExtraction.item_id
        ).filter(
            ArticleContent.scrape_success == True,
            AIExtraction.summary_complete == True,
            ~RawItem.id.in_(session.query(MasterItem.item_id)),
            ~RawItem.id.in_(session.query(RejectedItem.item_id))
        ).order_by(
            RawItem.published_date.desc()
        ).limit(limit).all()

        digest_items = []
        for item in items:
            extraction = session.query(AIExtraction).filter_by(item_id=item.id).first()

            digest_items.append(DigestItem(
                item_id=item.id,
                title=item.title,
                company=extraction.company if extraction else None,
                deal_amount=extraction.deal_amount if extraction else None,
                deal_type=extraction.transaction_type or (extraction.deal_type if extraction else None),
                sectors=extraction.sectors if extraction else None,
                summary=extraction.strategic_significance or (extraction.ai_summary if extraction else None),
                url=item.url,
                relevance_score=item.relevance_score
            ))

        return digest_items

    finally:
        session.close()


def send_pending_digest(limit: int = 20, dry_run: bool = False) -> bool:
    """Send email digest with pending items.

    Args:
        limit: Maximum items to include
        dry_run: If True, print items but don't send email

    Returns:
        True if successful
    """
    items = get_pending_items(limit)

    if not items:
        print("No pending items with AI summaries found")
        return True

    print(f"Found {len(items)} pending items:")
    for item in items:
        print(f"  - [{item.item_id}] {item.company or 'Unknown'}: {item.title[:60]}...")

    if dry_run:
        print("\nDry run - not sending email")
        return True

    return send_digest_email(items)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Send digest email with pending items")
    parser.add_argument("--limit", type=int, default=20, help="Max items to include")
    parser.add_argument("--dry-run", action="store_true", help="Print items without sending")

    args = parser.parse_args()

    success = send_pending_digest(limit=args.limit, dry_run=args.dry_run)
    sys.exit(0 if success else 1)
