"""Parse free-text investor strings into structured data."""

import re
import unicodedata


def slugify(name):
    """Convert investor name to URL-safe slug.

    Examples:
        'Andreessen Horowitz' -> 'andreessen-horowitz'
        'L3Harris Technologies' -> 'l3harris-technologies'
    """
    # Normalize unicode characters
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    # Lowercase
    name = name.lower()
    # Replace non-alphanumeric with hyphens
    name = re.sub(r'[^a-z0-9]+', '-', name)
    # Strip leading/trailing hyphens
    name = name.strip('-')
    return name


def parse_investors(text):
    """Parse a free-text investors string into structured list.

    Handles comma-separated lists, parenthetical annotations like "(lead)",
    and common formatting variations.

    Args:
        text: Free-text investors string, e.g. "Andreessen Horowitz (lead), General Catalyst, Lux Capital"

    Returns:
        List of tuples: [(name, is_lead), ...]
        Deduplicated by slugified name, preserving first occurrence.
    """
    if not text or not text.strip():
        return []

    results = []
    seen_slugs = set()

    # Split on commas and semicolons
    parts = re.split(r'[,;]', text)

    # Prose phrases that prefix real names (AI extraction artifacts)
    _PROSE_PREFIXES = re.compile(
        r'^(?:'
        r'also\s+including|including'
        r'|as\s+well\s+as|along\s+with|alongside'
        r'|backed\s+by|led\s+by|co-?led\s+by|joined\s+by'
        r'|with\s+participation\s+from|with\s+participation\s+by'
        r'|with\s+previous\s+backers|previous\s+backers'
        r'|existing\s+backers|new\s+investors\s+include'
        r'|and\s+also|and|also|plus|with'
        r')\s+',
        re.IGNORECASE
    )

    # Trailing annotations to strip (e.g. "as acquirer", "as seller")
    _TRAILING_JUNK = re.compile(
        r'\s+(?:as\s+acquirer|as\s+seller|as\s+lead\s+investor|private\s+equity\s+firm.*)',
        re.IGNORECASE
    )

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Skip tokens that are prose sentences, not investor names
        if len(part) > 80:
            continue

        # Strip leading prose phrases — apply repeatedly to handle stacked phrases
        # e.g. "with previous backers including Foo" → "including Foo" → "Foo"
        while True:
            stripped = _PROSE_PREFIXES.sub('', part).strip()
            if stripped == part:
                break
            part = stripped
        if not part:
            continue

        # Check for (lead) annotation
        is_lead = False
        lead_match = re.search(r'\s*\(lead\)\s*', part, re.IGNORECASE)
        if lead_match:
            is_lead = True
            part = part[:lead_match.start()] + part[lead_match.end():]

        # Strip other parentheticals (e.g., "(co-lead)", "(existing investor)")
        # Replace with a space to avoid adjacent words merging ("Holdingsas acquirer")
        part = re.sub(r'\s*\([^)]*\)\s*', ' ', part).strip()

        # Strip trailing prose annotations (e.g. "as acquirer", "as seller")
        part = _TRAILING_JUNK.sub('', part).strip()

        if not part:
            continue

        slug = slugify(part)
        if slug and slug not in seen_slugs:
            seen_slugs.add(slug)
            results.append((part, is_lead))

    return results
