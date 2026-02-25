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
- General stock market commentary without a specific deal
- Think tank reports or opinion pieces without a specific transaction

Review each article:

{titles_text}

Return a JSON array with one object per article, in order:
[
  {{"id": 1, "relevant": true, "reason": "Series B funding for defense AI company"}},
  {{"id": 2, "relevant": false, "reason": "Government budget debate, not a business deal"}}
]

Be selective. When in doubt about borderline cases, mark as relevant — a human will do final review. But obvious non-deals (politics, protests, legal cases, general news) should be filtered out."""

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

        return output

    except Exception as e:
        print(f"  Error in title screening: {e}")
        raise


def screen_titles(items):
    """
    Screen a list of items in batches.

    Args:
        items: list of dicts with 'id', 'title', 'summary', 'feed_source'

    Returns:
        dict: {id: {"relevant": bool, "reason": str}}
    """
    all_results = {}

    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Screening batch {batch_num}/{total_batches} ({len(batch)} titles)...")

        results = screen_title_batch(batch)
        all_results.update(results)

    return all_results
