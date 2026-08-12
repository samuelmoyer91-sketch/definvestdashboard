#!/usr/bin/env python3
"""Find out what a refused extraction can fall back to, and test it for real.

Some defense articles are declined by the biology safety classifier
(stop_reason=refusal, category=bio), so their extraction comes back empty and
the card lands in triage blank. Anthropic's own refusal message points at
configuring a fallback model.

This reports what the API says is permitted, then tries it against an article
that is ACTUALLY failing right now — which is the only test that settles it.

Read-only apart from API calls. Run via:
    gh workflow run migrate.yml -f script=probe_refusal_fallback.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic

from src.database.models import get_session, RawItem, ArticleContent, AIExtraction

MODEL = "claude-sonnet-5"

if not os.environ.get('ANTHROPIC_API_KEY'):
    print("ANTHROPIC_API_KEY not set")
    sys.exit(1)

client = anthropic.Anthropic()

print("=" * 70)
print("1. What does the API say this model may fall back to?")
print("=" * 70)
for beta in ("server-side-fallback-2026-06-01", "server-side-fallback-2026-07-01"):
    try:
        m = client.models.retrieve(MODEL, extra_headers={"anthropic-beta": beta})
        d = m.to_dict() if hasattr(m, 'to_dict') else dict(m)
        print(f"  [{beta}] allowed_fallback_models = {d.get('allowed_fallback_models', 'NOT PRESENT')}")
    except Exception as e:
        print(f"  [{beta}] retrieve failed: {type(e).__name__}: {e}")

print()
print("=" * 70)
print("2. Is the fallback parameter accepted at all? (trivial prompt)")
print("=" * 70)
forms = [
    ("default scalar", "server-side-fallback-2026-07-01", "default"),
    ("array / opus-4-8", "server-side-fallback-2026-06-01", [{"model": "claude-opus-4-8"}]),
]
accepted = []
for label, beta, value in forms:
    try:
        r = client.beta.messages.create(
            model=MODEL, max_tokens=16, betas=[beta], fallbacks=value,
            messages=[{"role": "user", "content": "Say OK."}])
        print(f"  {label:20s} ACCEPTED (stop_reason={r.stop_reason})")
        accepted.append((label, beta, value))
    except Exception as e:
        print(f"  {label:20s} rejected: {type(e).__name__}: {str(e)[:160]}")

print()
print("=" * 70)
print("3. Against an article that is ACTUALLY failing right now")
print("=" * 70)
session = get_session()
row = (session.query(RawItem, ArticleContent)
       .join(ArticleContent, ArticleContent.item_id == RawItem.id)
       .join(AIExtraction, AIExtraction.item_id == RawItem.id)
       .filter(AIExtraction.summary_complete == False,
               ArticleContent.scrape_success == True)
       .first())
if not row:
    print("  No currently-failing article found — nothing to test against.")
    sys.exit(0)

item, art = row
print(f"  item {item.id}: {item.title[:64]}")
text = (art.clean_text or '')[:25000]
prompt = f"Extract the company and deal amount from this article as JSON.\n\n{text}"

print("\n  a) WITHOUT a fallback (reproduce the failure):")
try:
    r = client.messages.create(model=MODEL, max_tokens=1000,
                               messages=[{"role": "user", "content": prompt}])
    txt = next((b.text for b in r.content if b.type == "text"), None)
    print(f"     stop_reason={r.stop_reason}  text={'yes' if txt else 'NONE'}")
    if r.stop_reason == 'refusal' and getattr(r, 'stop_details', None):
        print(f"     category={getattr(r.stop_details, 'category', None)}")
except Exception as e:
    print(f"     error: {type(e).__name__}: {e}")

# Server-side fallbacks are unavailable on this model, so the question becomes
# which OTHER model will answer the same prompt. Only a model that does not
# refuse is usable as a client-side retry target.
print("\n  b) Same prompt, other models:")
for cand in ("claude-sonnet-4-6", "claude-opus-4-8", "claude-haiku-4-5"):
    try:
        r = client.messages.create(model=cand, max_tokens=1000,
                                   messages=[{"role": "user", "content": prompt}])
        txt = next((b.text for b in r.content if b.type == "text"), None)
        cat = getattr(getattr(r, 'stop_details', None), 'category', None)
        print(f"     {cand:20s} stop_reason={r.stop_reason:10s} "
              f"{'ANSWERED: ' + txt[:70].replace(chr(10),' ') if txt else 'no text (category=' + str(cat) + ')'}")
    except Exception as e:
        print(f"     {cand:20s} error: {type(e).__name__}: {str(e)[:110]}")

for label, beta, value in accepted:
    print(f"\n  c) WITH fallbacks ({label}):")
    try:
        r = client.beta.messages.create(model=MODEL, max_tokens=1000,
                                        betas=[beta], fallbacks=value,
                                        messages=[{"role": "user", "content": prompt}])
        txt = next((b.text for b in r.content if b.type == "text"), None)
        served = getattr(r, 'model', '?')
        print(f"     stop_reason={r.stop_reason}  served_by={served}")
        print(f"     text={'YES — ' + txt[:110].replace(chr(10),' ') if txt else 'NONE'}")
    except Exception as e:
        print(f"     error: {type(e).__name__}: {str(e)[:200]}")

session.close()
