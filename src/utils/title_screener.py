#!/usr/bin/env python3
"""
AI-powered title screener for defense investment articles.

Uses Claude Haiku to do a cheap, fast relevance check on article titles
and RSS summaries BEFORE scraping or full AI extraction. Filters out
articles that match keywords but aren't actually about defense business deals.

Inserted in pipeline between RSS fetch and article scraping.
"""

import os
import json
from anthropic import Anthropic


BATCH_SIZE = 25  # Titles per API call


def screen_title_batch(items):
    """
    Screen a batch of article titles for relevance using Claude Haiku.

    Args:
        items: list of dicts with 'id', 'title', 'summary', 'feed_source'

    Returns:
        dict: {id: {"relevant": bool, "reason": str}}
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("  Warning: ANTHROPIC_API_KEY not set. Passing all items through.")
        return {item['id']: {"relevant": True, "reason": "No API key"} for item in items}

    client = Anthropic(api_key=api_key)

    # Build the numbered list of titles
    title_list = []
    for i, item in enumerate(items, 1):
        summary_snippet = (item['summary'] or '')[:150]
        title_list.append(f"{i}. [{item['feed_source']}] {item['title']}\n   Summary: {summary_snippet}")

    titles_text = "\n".join(title_list)

    prompt = f"""You are a filter for a defense/aerospace investment tracking system. Review these article titles and summaries. For each one, decide if it is likely about an actual BUSINESS event in the defense/aerospace sector.

RELEVANT articles are about:
- Investment deals (VC funding, PE acquisitions, mergers, IPOs)
- New factories, facilities, or manufacturing expansions for defense/aerospace
- Corporate strategic partnerships or joint ventures in defense
- Defense company financial results, capex, or R&D spending
- Production capacity grants or industrial base expansion programs

NOT RELEVANT articles are about:
- Routine government contracts and awards (e.g., "$50M contract to supply X", task orders, delivery orders, IDIQ awards) — UNLESS they involve industrial base expansion, new facility construction, or production capacity grants
- Government policy, budgets, or political debates (unless a specific contract/deal)
- Legal/criminal cases (even if defense-related keywords appear)
- Geopolitical news, military operations, or troop movements
- Social issues, protests, immigration enforcement
- Sports, entertainment, personal finance, non-defense industries
- Market commentary, forecasts, or outlooks (e.g., "defense stocks set for banner year", "analysts bullish on aerospace sector", "why defense is a good investment in 2025") — no specific transaction
- Think tank reports, opinion pieces, or analyst notes without a specific transaction
- Earnings/quarterly results articles unless they announce a specific deal, acquisition, or major capex program
- Articles about a company's stock price movement without an underlying transaction
- Lists, rankings, or "best of" articles (e.g., "top 10 defense stocks to watch")
- Speculative or intent-based articles where no deal has been formally announced (e.g., "Company X plans to expand", "XYZ considering acquisition", "Defense firm eyes investment", "could build new facility") — plans and intentions are not transactions

The key test: does the article describe a SPECIFIC transaction that has already occurred or been formally announced — a named company raising or deploying a specific amount of capital for a specific purpose? If no specific transaction exists, or if the language is speculative/forward-looking ("plans to", "considering", "exploring", "eyes", "mulls", "could", "may expand", "expected to"), filter it out. Intentions and rumors are not deals.

Review each article:

{titles_text}

Return a JSON array with one object per article, in order:
[
  {{"id": 1, "relevant": true, "reason": "Series B funding for defense AI company"}},
  {{"id": 2, "relevant": false, "reason": "Market outlook piece, no specific deal"}}
]

Be selective. If the title sounds like news commentary, a forecast, or general industry analysis rather than a specific business event, filter it out. Only pass through articles that are likely reporting on a concrete transaction."""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text

        # Parse JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        results = json.loads(response_text)

        # Map back to item IDs
        output = {}
        for i, result in enumerate(results):
            if i < len(items):
                item_id = items[i]['id']
                output[item_id] = {
                    "relevant": result.get("relevant", True),
                    "reason": result.get("reason", "")
                }

        # Any items not in response default to relevant (safe fallback)
        for item in items:
            if item['id'] not in output:
                output[item['id']] = {"relevant": True, "reason": "Not in AI response (defaulting to relevant)"}

        return output, {"input_tokens": message.usage.input_tokens, "output_tokens": message.usage.output_tokens}

    except Exception as e:
        print(f"  Error in title screening: {e}")
        raise


def screen_titles(items):
    """
    Screen a list of items in batches.

    Args:
        items: list of dicts with 'id', 'title', 'summary', 'feed_source'

    Returns:
        tuple: (results_dict, total_input_tokens, total_output_tokens)
               results_dict: {id: {"relevant": bool, "reason": str}}
    """
    all_results = {}
    total_input = 0
    total_output = 0

    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Screening batch {batch_num}/{total_batches} ({len(batch)} titles)...")

        results, usage = screen_title_batch(batch)
        all_results.update(results)
        total_input += usage["input_tokens"]
        total_output += usage["output_tokens"]

    return all_results, total_input, total_output
