"""Claude API pricing constants and cost calculation.

Single source of truth for model pricing. Update here when Anthropic
changes rates; all pipeline scripts and the costs page derive from this.

Prices are in USD per 1,000,000 tokens (MTok).
"""

MODEL_PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-20250514":  {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-6":         {"input": 3.00, "output": 15.00},
    "claude-sonnet-5":           {"input": 2.00, "output": 10.00},  # intro pricing through 2026-08-31, then $3/$15
}

# Human-readable labels for the costs page
MODEL_LABELS = {
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    "claude-sonnet-4-20250514":  "Claude Sonnet 4",
    "claude-sonnet-4-6":         "Claude Sonnet 4.6",
    "claude-sonnet-5":           "Claude Sonnet 5",
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return cost in USD for a given model and token counts."""
    p = MODEL_PRICING.get(model, {"input": 3.00, "output": 15.00})
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000
