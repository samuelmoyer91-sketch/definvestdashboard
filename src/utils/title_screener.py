#!/usr/bin/env python3
"""
AI-powered title screener for defense investment articles.

Uses Claude to do a relevance check on article titles and RSS summaries
BEFORE scraping or full AI extraction. Filters out
articles that match keywords but aren't actually about defense business deals.

Inserted in pipeline between RSS fetch and article scraping.
"""

import os
import json
from anthropic import Anthropic


BATCH_SIZE = 25  # Titles per API call


def screen_title_batch(items):
    """
    Screen a batch of article titles for relevance using Claude.

    Args:
        items: list of dicts with 'id', 'title', 'summary', 'feed_source'

    Returns:
        dict: {id: {"relevant": bool, "reason": str}}
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("  Warning: ANTHROPIC_API_KEY not set. Passing all items through.")
        return (
            {item['id']: {"relevant": True, "reason": "No API key"} for item in items},
            {"input_tokens": 0, "output_tokens": 0},
        )

    client = Anthropic(api_key=api_key)

    # Build the numbered list of titles
    title_list = []
    for i, item in enumerate(items, 1):
        summary_snippet = (item['summary'] or '')[:150]
        title_list.append(f"{i}. [{item['feed_source']}] {item['title']}\n   Summary: {summary_snippet}")

    titles_text = "\n".join(title_list)

    prompt = f"""You are a filter for a defense/aerospace investment tracking system. A human triages everything that passes this filter — they have capacity, so when in doubt, PASS IT THROUGH. Only filter out items that are clearly not about a defense/aerospace business event.

RELEVANT (pass through):
- Investment deals (VC funding, PE acquisitions, mergers, IPOs) involving a defense, aerospace, space, dual-use, or national-security company
- Defense-focused VCs or PE funds raising new funds (e.g., Shield Capital, Paladin, Razor's Edge, Harpoon Ventures, In-Q-Tel, a16z American Dynamism, Booz Allen Ventures)
- New factories, facilities, or manufacturing expansions for defense/aerospace
- Corporate strategic partnerships, joint ventures, or major capex/R&D announcements in defense
- Production capacity grants or industrial-base expansion programs
- Reported but not-yet-closed deals from major outlets (TechCrunch, CNBC, Bloomberg, Reuters, WSJ, Financial Times, Defense News, Breaking Defense, DefenseScoop, SpaceNews, The Information, Axios, Fortune) when a SPECIFIC company and SPECIFIC dollar amount are named — even if hedged with "sources say," "reportedly," "is in talks to," etc. The human will decide.
- Cybersecurity deals where any defense/government/IC angle is plausible — pass through and let the human decide. Only filter purely commercial cyber (consumer privacy, identity/access, SaaS security with no government angle).

NOT RELEVANT (filter out):
- Routine government contracts and task/delivery orders (e.g., "$50M contract to supply X") UNLESS they involve facility construction, capacity expansion, or industrial-base programs
- Government policy, budgets, or political debates with no specific transaction
- Legal/criminal cases (even with defense-related keywords)
- Geopolitical news, military operations, troop movements, war reporting, weapons used in combat
- Sports (including hockey/basketball "defense"), entertainment, obituaries, social issues, immigration enforcement
- Market commentary, forecasts, analyst notes, "outlook" pieces, rankings ("top 10 defense stocks"), opinion pieces, think tank reports — anything that is not reporting a concrete event
- Earnings/quarterly results UNLESS they announce a specific new deal, acquisition, or major capex program
- Stock price movements, ETF news, share buybacks
- Vague speculative items with NO company and NO amount named (e.g., "PE firms eyeing defense sector" — no specific deal)

The bar to filter out is: the article is clearly NOT a defense business event. The bar to pass through is: the article COULD be a defense business event (specific company, specific deal, defense angle plausible). When uncertain, pass through.

Review each article:

{titles_text}

Return a JSON array with one object per article, in order:
[
  {{"id": 1, "relevant": true, "reason": "Series B funding for defense AI company"}},
  {{"id": 2, "relevant": false, "reason": "Market outlook piece, no specific deal"}}
]

Default to relevant=true when uncertain. The human triage step is fast and they prefer false positives to false negatives."""

    try:
        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = next(block.text for block in message.content if block.type == "text")

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
