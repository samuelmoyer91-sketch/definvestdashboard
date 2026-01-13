#!/usr/bin/env python3
"""
Generate AI summaries for scraped articles.

Run this after article_scraper.py to generate AI summaries for articles
that don't have them yet.
"""

import sys
from pathlib import Path
import time

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import RawItem, ArticleContent, AIExtraction, get_session
from src.utils.ai_summarizer import summarize_deal_article, format_summary_for_display


def generate_summaries(limit=5, force_regenerate=False):
    """
    Generate AI summaries for articles.

    Args:
        limit: Max number of summaries to generate
        force_regenerate: If True, regenerate summaries even if they exist
    """

    session = get_session()

    # Find articles that need summaries
    query = session.query(RawItem).join(ArticleContent).outerjoin(AIExtraction)

    if force_regenerate:
        # Regenerate all that have article content
        items = query.filter(
            ArticleContent.scrape_success == True
        ).limit(limit).all()
    else:
        # Only generate for items without complete summaries
        # Include items with no AI extraction OR incomplete extractions
        from sqlalchemy import or_
        items = query.filter(
            ArticleContent.scrape_success == True,
            or_(
                AIExtraction.id == None,  # No AI extraction yet
                AIExtraction.summary_complete == False,  # Incomplete extraction
                AIExtraction.summary_complete == None  # Null summary_complete
            )
        ).limit(limit).all()

    if not items:
        print("No items need AI summaries!")
        session.close()
        return 0, 0

    print("=" * 80)
    print(f"GENERATING AI SUMMARIES FOR {len(items)} ARTICLES")
    print("=" * 80)
    print()

    success_count = 0
    error_count = 0

    for i, item in enumerate(items, 1):
        print(f"[{i}/{len(items)}] {item.title[:60]}...")

        # Get article content
        article = item.article

        try:
            # Generate AI summary
            summary = summarize_deal_article(
                article_text=article.clean_text,
                article_title=item.title,
                article_url=item.url
            )

            # Check if extraction exists
            extraction = session.query(AIExtraction).filter_by(item_id=item.id).first()

            if extraction:
                # Update existing
                extraction.company = summary.get('company_name')
                extraction.company_description = summary.get('company_description')
                extraction.deal_type = summary.get('deal_type')  # Legacy
                extraction.deal_amount = summary.get('deal_amount')
                extraction.investors = summary.get('investors')
                # New enhanced category fields
                extraction.transaction_type = summary.get('transaction_type')
                extraction.capital_sources = ','.join(summary.get('capital_sources', [])) if summary.get('capital_sources') else None
                extraction.sectors = ','.join(summary.get('sectors', [])) if summary.get('sectors') else None
                extraction.strategic_significance = summary.get('strategic_significance')
                extraction.market_implications = summary.get('market_implications')
                extraction.summary_complete = summary.get('summary_complete', False)
                extraction.model_used = summary.get('model_used')
            else:
                # Create new
                extraction = AIExtraction(
                    item_id=item.id,
                    company=summary.get('company_name'),
                    company_description=summary.get('company_description'),
                    deal_type=summary.get('deal_type'),  # Legacy
                    deal_amount=summary.get('deal_amount'),
                    investors=summary.get('investors'),
                    # New enhanced category fields
                    transaction_type=summary.get('transaction_type'),
                    capital_sources=','.join(summary.get('capital_sources', [])) if summary.get('capital_sources') else None,
                    sectors=','.join(summary.get('sectors', [])) if summary.get('sectors') else None,
                    strategic_significance=summary.get('strategic_significance'),
                    market_implications=summary.get('market_implications'),
                    summary_complete=summary.get('summary_complete', False),
                    model_used=summary.get('model_used')
                )
                session.add(extraction)

            session.commit()

            if summary.get('summary_complete'):
                success_count += 1
                print(f"  ✓ Generated summary")
                # Optionally print summary for review
                # print(format_summary_for_display(summary))
            else:
                error_count += 1
                print(f"  ⚠️  Summary incomplete (no API key or error)")

        except Exception as e:
            error_count += 1
            print(f"  ✗ Error: {e}")

        # Rate limiting (Claude API has limits)
        if i < len(items):
            time.sleep(1)  # 1 second between requests

    print()
    print("=" * 80)
    print(f"SUMMARY: {success_count} successful, {error_count} failed/incomplete")
    print("=" * 80)

    session.close()

    return success_count, error_count


if __name__ == '__main__':
    import os
    os.chdir(Path(__file__).parent.parent.parent)

    # Parse arguments
    limit = 5
    force = False

    if len(sys.argv) > 1:
        if sys.argv[1] == '--force':
            force = True
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        elif sys.argv[1] == '--limit' and len(sys.argv) > 2:
            limit = int(sys.argv[2])
        else:
            try:
                limit = int(sys.argv[1])
            except ValueError:
                print("Usage: python3 generate_ai_summaries.py [--limit N] [--force]")
                sys.exit(1)

    generate_summaries(limit=limit, force_regenerate=force)
