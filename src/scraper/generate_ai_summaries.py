#!/usr/bin/env python3
"""
Generate AI summaries for scraped articles.

Run this after article_scraper.py to generate AI summaries for articles
that don't have them yet.
"""

import sys
from pathlib import Path
import time
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import RawItem, ArticleContent, AIExtraction, ApiUsageLog, get_session
from src.database.models import _reset_turso_connection
from src.utils.ai_summarizer import summarize_deal_article, format_summary_for_display
from src.utils.pricing import calculate_cost

SONNET_MODEL = "claude-sonnet-4-20250514"


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
    total_input_tokens = 0
    total_output_tokens = 0

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

            # capital_source is now an array; join to comma-separated string for storage
            cap_src_raw = summary.get('capital_source') or summary.get('capital_sources')
            if isinstance(cap_src_raw, list):
                cap_src = ','.join(cap_src_raw) if cap_src_raw else None
            elif isinstance(cap_src_raw, str):
                cap_src = cap_src_raw if cap_src_raw else None
            else:
                cap_src = None

            if extraction:
                # Update existing
                extraction.title = summary.get('title')
                extraction.company = summary.get('company_name')
                extraction.deal_type = summary.get('deal_type')  # Legacy
                extraction.transaction_type = summary.get('transaction_type')
                extraction.deal_amount = summary.get('deal_amount')
                extraction.investors = summary.get('investors')
                extraction.capital_sources = cap_src
                extraction.sectors = ','.join(summary.get('sectors', [])) if summary.get('sectors') else None
                extraction.location = summary.get('location')
                extraction.strategic_significance = summary.get('strategic_significance')
                extraction.deal_status = summary.get('deal_status')
                extraction.summary_complete = summary.get('summary_complete', False)
                extraction.model_used = summary.get('model_used')
            else:
                # Create new
                extraction = AIExtraction(
                    item_id=item.id,
                    title=summary.get('title'),
                    company=summary.get('company_name'),
                    deal_type=summary.get('deal_type'),  # Legacy
                    transaction_type=summary.get('transaction_type'),
                    deal_amount=summary.get('deal_amount'),
                    investors=summary.get('investors'),
                    capital_sources=cap_src,
                    sectors=','.join(summary.get('sectors', [])) if summary.get('sectors') else None,
                    location=summary.get('location'),
                    strategic_significance=summary.get('strategic_significance'),
                    deal_status=summary.get('deal_status'),
                    summary_complete=summary.get('summary_complete', False),
                    model_used=summary.get('model_used')
                )
                session.add(extraction)

            try:
                session.commit()
            except BaseException as e:
                print(f"  ⚠ DB commit failed ({e}), resetting connection and retrying...")
                try:
                    session.rollback()
                except BaseException:
                    pass
                _reset_turso_connection()
                session = get_session()
                try:
                    session.add(extraction)
                    session.commit()
                except BaseException as e2:
                    print(f"  ✗ Retry commit also failed: {e2}")
                    error_count += 1
                    continue

            total_input_tokens += summary.get('input_tokens', 0)
            total_output_tokens += summary.get('output_tokens', 0)

            if summary.get('summary_complete'):
                success_count += 1
                print(f"  ✓ Generated summary")
            else:
                error_count += 1
                print(f"  ⚠️  Summary incomplete (no API key or error)")

        except Exception as e:
            error_count += 1
            print(f"  ✗ Error: {e}")

        # Rate limiting (Claude API has limits)
        if i < len(items):
            time.sleep(1)  # 1 second between requests

    # Log API usage
    if total_input_tokens > 0:
        try:
            cost = calculate_cost(SONNET_MODEL, total_input_tokens, total_output_tokens)
            log = ApiUsageLog(
                logged_at=datetime.utcnow(),
                run_type='summarizer',
                model=SONNET_MODEL,
                items_processed=len(items),  # items attempted (success + error)
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cost_usd=cost,
            )
            session.add(log)
            session.commit()
            print(f"API usage logged: {total_input_tokens:,} in / {total_output_tokens:,} out — ${cost:.4f}")
        except Exception as e:
            print(f"Warning: failed to log API usage: {e}")

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
