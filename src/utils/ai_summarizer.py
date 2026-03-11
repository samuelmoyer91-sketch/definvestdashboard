#!/usr/bin/env python3
"""
AI-powered article summarizer for defense investment deals.

Uses Claude API to extract structured information from scraped articles:
- Company name, location
- Capital type and deal amount
- Key investors/acquirers
- Sectors (technology areas)
- Strategic significance and market implications
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
{article_text[:25000]}

Extract the following information (use "Unknown" if not found):

1. TITLE: Write a concise analyst-style headline (5-10 words). Always lead with the company name. Use present-tense action verbs: "Raises", "Acquires", "Builds", "Invests", "Opens". Include the dollar amount when known. Strip all journalistic fluff — no "to meet growing demand", no source attributions, no filler. Use industry shorthand where appropriate (e.g., "PE Fund", "PNT", "Space Tech"). Never be vague — always name the company (not "Startup raises..." or "Company confirms..."). Examples: "Safran Acquires Syntony for PNT", "GRVTY Invests $8M in Virginia Facility", "Veritas Raises $15.3B PE Fund for Defense Investments", "GE Aerospace Builds Manufacturing Facilities". Do NOT copy the article headline — rewrite it shorter and cleaner.
2. COMPANY NAME: The company being invested in or acquired
3. CAPITAL TYPE: Choose ALL that apply from: Seed, Venture Capital, Private Equity, Corporate M&A, Government Support, Public Markets, Internal/Self-funded, Fund Raise. Most deals have one type, but select multiple when genuinely applicable (e.g., a round with both VC and Government/Contract components). "Seed" = pre-Series A/angel. "Venture Capital" = Series A through late-stage VC rounds. "Private Equity" = PE acquisitions, PE growth equity. "Corporate M&A" = operating company acquires another (no PE sponsor). "Government Support" = government contracts, SBIR, grants, government equity stakes. "Public Markets" = IPO, SPAC, secondary offerings. "Internal/Self-funded" = capex, facility builds from balance sheet. "Fund Raise" = VC or PE fund raising capital from LPs (e.g., "Veritas raises $15B fund"), NOT deploying capital into a company. Return as array.
4. TRANSACTION TYPE: Choose exactly one from: "Equity Funding Round", "Acquisition", "Merger", "IPO", "Strategic Partnership", "Internal Investment", "Contract/Award", "Government Support", "Fund Raise". "Equity Funding Round" = company raises equity capital (Seed through late-stage VC, PE growth equity). "Acquisition" = one company buys another outright. "Merger" = two companies combine. "IPO" = company goes public. "Strategic Partnership" = joint venture, teaming agreement, licensing deal, or non-equity collaboration. "Internal Investment" = company invests in itself from its own balance sheet (facilities, R&D capex). "Contract/Award" = routine government procurement contract, SBIR/STTR award, or government grant — the government is buying a deliverable or rewarding a small R&D project. "Government Support" = government makes a direct investment in a company's productive capacity — Title III of the Defense Production Act, Industrial Base Fund investments, DIU OTAs with capital/equity components, AFWERX STRATFI/TACFI, or similar programs where DoD is funding a company to build or expand a capability (not just buying a deliverable). "Fund Raise" = VC/PE fund raising LP capital. Return as a single string.
5. SECTORS: Choose ALL that apply from: Autonomous Systems/Drones, AI/ML, Space/Satellites, Aerospace, Cybersecurity, Advanced Materials, Semiconductors/Electronics, Manufacturing/Production, Software/IT, Munitions/Weapons, Communications, Electronic Warfare, Other (return as array)
6. DEAL AMOUNT: Dollar value if mentioned (e.g., "$300M" or "$4.7B")
7. INVESTORS/ACQUIRERS: Key firms or companies involved. Return as a clean comma-separated list of names only — no descriptions, no parentheticals, no "led by", "backed by", "with participation from", or other connective language. Example: "8VC, Lux Capital, Founders Fund". For self-funded/internal deals, return "Self-funded".
8. LOCATION: Where the company is headquartered or where the deal/project is located. Format as "City, State, Country" for US locations (e.g., "San Diego, CA, USA") or "City, Country" for international (e.g., "London, UK"). Use null if not mentioned.
9. STRATEGIC SIGNIFICANCE: In 2-3 sentences, describe specifically what the company will do with this capital — which products, programs, facilities, or capabilities it will fund or develop. Name them explicitly; do not generalize. If the investor or fund is not well-known or has an unusual structure (e.g., a government-backed development bank, a sector-specific fund), briefly explain what it is and what it invests in. Be factual and specific. Do not editorialize about why this matters, what it signals, or how it positions the company. Write in third person present tense. Example style: "AeroVironment is significantly expanding domestic manufacturing capacity for directed energy laser systems, anti-drone systems, and laser communications. State and local resourcing include $5 million from the state of New Mexico and $1 million from the City of Albuquerque."

Format your response as JSON:
{{
  "title": "...",
  "company_name": "...",
  "capital_source": ["...", "..."],
  "transaction_type": "...",
  "sectors": ["...", "..."],
  "deal_amount": "...",
  "investors": "...",
  "location": "City, State, Country",
  "strategic_significance": "..."
}}

Notes:
- capital_source is an array — include all that apply, but don't over-select; most deals have one type
- transaction_type is a single string — pick the single best-fit category
- For sectors: include all relevant technology areas the company operates in
- Be professional and analytical (intelligence briefing tone). If information is missing or unclear, use "Unknown" rather than guessing.

Special handling for EARNINGS CALLS, ANNUAL REPORTS, and INVESTOR PRESENTATIONS:
- These are about a company's own spending, not an external deal. Use capital_source "Internal/Self-funded".
- For deal_amount: use the single most significant capex or R&D figure mentioned. If multiple figures, pick the headline number (total R&D budget or largest single investment). It's OK to leave this null if no clear figure stands out.
- For investors: leave null.
- For strategic_significance: describe specifically where the company is directing spending — which programs, capabilities, or facilities. Name them explicitly. Do not editorialize.
- Treat the article as ONE card for the company, not separate cards per spending line item."""

    try:
        # Call Claude API
        message = client.messages.create(
            model="claude-sonnet-4-20250514",  # Latest Sonnet model
            max_tokens=2048,
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
        summary_data['input_tokens'] = message.usage.input_tokens
        summary_data['output_tokens'] = message.usage.output_tokens

        return summary_data

    except Exception as e:
        print(f"⚠️  Error generating AI summary: {e}")
        return {
            'company_name': None,
            'deal_amount': None,
            'investors': None,
            'strategic_significance': None,
            'market_implications': None,
            'summary_complete': False,
            'input_tokens': 0,
            'output_tokens': 0,
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
