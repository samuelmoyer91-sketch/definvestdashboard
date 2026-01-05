#!/usr/bin/env python3
"""
AI-powered article summarizer for defense investment deals.

Uses Claude API to extract structured information from scraped articles:
- Company name and description
- Deal type (VC/M&A/IPO) and amount
- Key investors/acquirers
- Strategic significance
- Market implications
"""

import os
import json
from anthropic import Anthropic

def summarize_deal_article(article_text, article_title, article_url):
    """
    Generate AI summary of a defense deal article.

    Args:
        article_text: Full article text
        article_title: Article headline
        article_url: Source URL

    Returns:
        dict with extracted fields (may have None values for missing data)
    """

    # Check for API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠️  Warning: ANTHROPIC_API_KEY not set. Returning empty summary.")
        return {
            'company_name': None,
            'company_description': None,
            'deal_type': None,
            'deal_amount': None,
            'investors': None,
            'strategic_significance': None,
            'market_implications': None,
            'summary_complete': False
        }

    # Initialize Claude client
    client = Anthropic(api_key=api_key)

    # Craft the extraction prompt
    prompt = f"""Analyze this defense/aerospace investment article and extract key information. Be concise and factual.

Article Title: {article_title}
Article URL: {article_url}

Article Text:
{article_text[:8000]}

Extract the following information (use "Unknown" if not found):

1. COMPANY NAME: The company being invested in or acquired
2. COMPANY DESCRIPTION: One sentence describing what the company does (focus on defense/tech capabilities)
3. DEAL TYPE: Is this VC funding, M&A acquisition, IPO, or other?
4. DEAL AMOUNT: Dollar value if mentioned (e.g., "$300M" or "$4.7B")
5. INVESTORS/ACQUIRERS: Key firms or companies involved
6. STRATEGIC SIGNIFICANCE: Why does this deal matter for defense sector? (2-3 sentences max)
7. MARKET IMPLICATIONS: What does this signal about defense tech trends? (1-2 sentences)

Format your response as JSON:
{{
  "company_name": "...",
  "company_description": "...",
  "deal_type": "...",
  "deal_amount": "...",
  "investors": "...",
  "strategic_significance": "...",
  "market_implications": "..."
}}

Be professional and analytical (intelligence briefing tone). If information is missing or unclear, use "Unknown" rather than guessing."""

    try:
        # Call Claude API
        message = client.messages.create(
            model="claude-sonnet-4-20250514",  # Latest Sonnet model
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract response
        response_text = message.content[0].text

        # Parse JSON from response
        # Claude sometimes wraps JSON in markdown code blocks
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        summary_data = json.loads(response_text)

        # Add metadata
        summary_data['summary_complete'] = True
        summary_data['model_used'] = 'claude-sonnet-4-20250514'

        return summary_data

    except Exception as e:
        print(f"⚠️  Error generating AI summary: {e}")
        return {
            'company_name': None,
            'company_description': None,
            'deal_type': None,
            'deal_amount': None,
            'investors': None,
            'strategic_significance': None,
            'market_implications': None,
            'summary_complete': False,
            'error': str(e)
        }


def format_summary_for_display(summary_dict):
    """
    Format AI summary for human-readable display.

    Args:
        summary_dict: Output from summarize_deal_article()

    Returns:
        Formatted string for terminal/UI display
    """

    if not summary_dict.get('summary_complete'):
        return "⚠️  AI summary not available"

    output = []
    output.append("=" * 60)
    output.append("AI SUMMARY")
    output.append("=" * 60)

    if summary_dict.get('company_name'):
        output.append(f"Company: {summary_dict['company_name']}")

    if summary_dict.get('company_description'):
        output.append(f"Description: {summary_dict['company_description']}")

    if summary_dict.get('deal_type') or summary_dict.get('deal_amount'):
        deal_info = []
        if summary_dict.get('deal_type'):
            deal_info.append(summary_dict['deal_type'])
        if summary_dict.get('deal_amount'):
            deal_info.append(summary_dict['deal_amount'])
        output.append(f"Deal: {' · '.join(deal_info)}")

    if summary_dict.get('investors'):
        output.append(f"Investors: {summary_dict['investors']}")

    if summary_dict.get('strategic_significance'):
        output.append(f"\nStrategic Significance:")
        output.append(f"  {summary_dict['strategic_significance']}")

    if summary_dict.get('market_implications'):
        output.append(f"\nMarket Implications:")
        output.append(f"  {summary_dict['market_implications']}")

    output.append("=" * 60)

    return "\n".join(output)


if __name__ == '__main__':
    # Test with sample article
    test_article = """
    Shield AI, a defense technology company developing AI-powered autonomous systems,
    announced today that it has raised $300 million in Series E funding. The round was
    led by Andreessen Horowitz, with participation from existing investors including
    Point72 Ventures and Riot Ventures.

    The San Diego-based company develops AI pilots for military aircraft, enabling
    autonomous flight in GPS-denied environments. Shield AI's technology has been
    deployed on multiple DoD platforms.

    The funding will accelerate development of the company's Hivemind AI pilot system
    and expand deployment across fixed-wing and rotary aircraft. This represents the
    largest venture capital investment in defense AI this year.
    """

    summary = summarize_deal_article(
        article_text=test_article,
        article_title="Shield AI Raises $300M Series E",
        article_url="https://example.com/shield-ai-funding"
    )

    print(format_summary_for_display(summary))
    print("\nRaw JSON:")
    print(json.dumps(summary, indent=2))
