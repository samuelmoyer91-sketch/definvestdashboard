"""
Relevance scoring for RSS feed items.

Created: 2026-01-22
Purpose: Filter out irrelevant articles early in the pipeline using keyword matching.
"""

import re
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def load_scoring_config(config_path='config/feeds.json'):
    """Load keyword configuration for scoring."""
    path = Path(config_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    with open(path, 'r') as f:
        return json.load(f)


def calculate_relevance_score(title, summary, config=None):
    """
    Calculate relevance score for an article based on keyword matching.

    Args:
        title: Article title
        summary: RSS summary/description
        config: Optional config dict (loads from feeds.json if not provided)

    Returns:
        tuple: (score: float 0.0-1.0, matched_keywords: list, exclude_matched: list)

    Scoring logic:
        - Each high_priority keyword match in title: +0.15
        - Each high_priority keyword match in summary: +0.08
        - Each deal_indicators match: +0.12 (strong signal)
        - Each exclude keyword match: -0.25
        - Maximum score capped at 1.0, minimum at 0.0
    """
    if config is None:
        config = load_scoring_config()

    keywords = config.get('keywords', {})
    high_priority = keywords.get('high_priority', [])
    exclude = keywords.get('exclude', [])
    deal_indicators = keywords.get('deal_indicators', [])

    # Combine and lowercase text for matching
    title_lower = (title or '').lower()
    summary_lower = (summary or '').lower()
    combined = f"{title_lower} {summary_lower}"

    score = 0.0
    matched_keywords = []
    exclude_matched = []

    # Check high priority keywords
    for keyword in high_priority:
        keyword_lower = keyword.lower()
        # Use word boundary matching to avoid partial matches
        pattern = r'\b' + re.escape(keyword_lower) + r'\b'

        if re.search(pattern, title_lower):
            score += 0.15
            if keyword not in matched_keywords:
                matched_keywords.append(keyword)
        elif re.search(pattern, summary_lower):
            score += 0.08
            if keyword not in matched_keywords:
                matched_keywords.append(keyword)

    # Check deal indicators (stronger signal)
    for indicator in deal_indicators:
        indicator_lower = indicator.lower()
        pattern = r'\b' + re.escape(indicator_lower) + r'\b'

        if re.search(pattern, combined):
            score += 0.12
            if indicator not in matched_keywords:
                matched_keywords.append(f"[deal]{indicator}")

    # Check exclude keywords (penalty)
    for keyword in exclude:
        keyword_lower = keyword.lower()
        pattern = r'\b' + re.escape(keyword_lower) + r'\b'

        if re.search(pattern, combined):
            score -= 0.25
            exclude_matched.append(keyword)

    # Clamp score to 0.0-1.0
    score = max(0.0, min(1.0, score))

    return score, matched_keywords, exclude_matched


def should_auto_reject(score, matched_keywords, exclude_matched, threshold=0.15):
    """
    Determine if an article should be auto-rejected.

    Args:
        score: Relevance score
        matched_keywords: List of matched positive keywords
        exclude_matched: List of matched exclude keywords
        threshold: Minimum score to keep (default 0.15)

    Returns:
        tuple: (should_reject: bool, reason: str)
    """
    # Auto-reject if exclude keywords dominate
    if exclude_matched and not matched_keywords:
        return True, f"Matched exclude keywords: {', '.join(exclude_matched)}"

    # Auto-reject if score is below threshold and no deal indicators
    deal_indicators_found = any(k.startswith('[deal]') for k in matched_keywords)
    if score < threshold and not deal_indicators_found:
        return True, f"Low relevance score ({score:.2f}) with no deal indicators"

    return False, None


def score_article_batch(articles, config=None):
    """
    Score a batch of articles and return with scores.

    Args:
        articles: List of dicts with 'title' and 'summary' keys
        config: Optional config dict

    Returns:
        List of dicts with added 'relevance_score', 'matched_keywords', 'auto_reject' keys
    """
    if config is None:
        config = load_scoring_config()

    results = []
    for article in articles:
        score, matched, excluded = calculate_relevance_score(
            article.get('title', ''),
            article.get('summary', ''),
            config
        )

        should_reject, reason = should_auto_reject(score, matched, excluded)

        result = article.copy()
        result['relevance_score'] = score
        result['matched_keywords'] = matched
        result['exclude_matched'] = excluded
        result['auto_reject'] = should_reject
        result['reject_reason'] = reason

        results.append(result)

    return results


if __name__ == '__main__':
    # Test the scorer with some sample titles
    test_cases = [
        ("Arlington Capital Partners to Sell Stellant Systems to TransDigm for $960 Million", "Defense contractor acquisition"),
        ("Capture of Maduro and US claim that it will run Venezuela raise new legal questions", "Breaking news about Venezuela"),
        ("Godspeed Capital-Backed Aurex Announces Acquisition of Alpha 2", "Private equity defense deal"),
        ("12 Willkie Partners Named to 2026 Lawdragon 500", "Law firm announcements"),
        ("Rocket Lab USA Soars as Massive Defense Deal Lands", "Defense space investment"),
        ("Wedding of local sports star announced", "Celebrity news"),
    ]

    print("=" * 80)
    print("RELEVANCE SCORER TEST")
    print("=" * 80)

    for title, summary in test_cases:
        score, matched, excluded = calculate_relevance_score(title, summary)
        should_reject, reason = should_auto_reject(score, matched, excluded)

        status = "❌ REJECT" if should_reject else "✓ KEEP"
        print(f"\n{status} (score: {score:.2f})")
        print(f"  Title: {title[:60]}...")
        if matched:
            print(f"  Matched: {', '.join(matched)}")
        if excluded:
            print(f"  Excluded: {', '.join(excluded)}")
        if reason:
            print(f"  Reason: {reason}")
