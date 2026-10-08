"""Keep placeholders and notes about the source out of deal fields.

The AI used to write "Unknown" into fields it could not fill, and sometimes
added a note about the article itself ("...though specific program details
are not disclosed in available reporting."). Both went straight into the
triage form, and whatever is in a box when Sam accepts is published: by
2026-10-07, 75 deals had no usable location, 14 had the investor "Unknown",
and two published summaries described the article's gaps. "Unknown" also
became an investor record, credited with 13 deals.

Used when an extraction is saved, when a triage card is shown, on accept and
edit, and by the investor parser, so an empty field stays empty.
"""
import re

# Values that mean "nothing here".
_PLACEHOLDERS = {
    '', 'unknown', 'none', 'null', 'n/a', 'na', 'tbd', 'not specified',
    'unspecified', 'not disclosed', 'undisclosed', 'not available', 'not stated',
    'not mentioned', 'not provided', 'various', 'others', '-', '—',
}


def is_placeholder(value):
    """True for None, blank, or a stand-in such as "Unknown" or "N/A"."""
    if value is None:
        return True
    return str(value).strip().strip('.').strip().lower() in _PLACEHOLDERS


def clean_value(value):
    """The value, or None when it is only a placeholder."""
    return None if is_placeholder(value) else str(value).strip()


# A sentence is a note about the source when it names the source...
_SOURCE = re.compile(
    r"\b(?:article|press\s+release|announcement|source\s+(?:text|material)|"
    r"(?:available|public)\s+(?:content|information|reporting|reports|sources?|text|materials?)|"
    r"page\s+content)\b"
    r"|\bpaywall", re.I)
# ...and says something is missing from it.
_GAP = re.compile(
    r"\b(?:not|no|nor|without|lacks?|lacking|n't|unavailable|inaccessible|absent|omits?)\b"
    r"|paywall", re.I)
# Where a trailing note usually begins: "X will build Y, though details are not disclosed."
_CLAUSE = re.compile(r",\s*(?:though|although|but|while|with\s+no|and\s+no)\b|;\s+|\s+[-—–]\s+", re.I)


def has_source_note(text):
    """True if any sentence comments on what the article does or doesn't say."""
    if not text:
        return False
    return any(_SOURCE.search(s) and _GAP.search(s) for s in _sentences(text))


def _sentences(text):
    return [s for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s]


def strip_source_notes(text):
    """Remove sentences, or trailing clauses, that comment on the source.

    "Acme is expanding X, though details are not disclosed in available
    reporting."  ->  "Acme is expanding X."
    "This article does not contain investment information."  ->  ""
    Statements of fact about the deal ("terms were not disclosed", "MySize has
    not identified targets") are kept: they don't mention the source.
    """
    if text is None:
        return None
    if not has_source_note(text):
        # Leave untouched text exactly as it was (line breaks included).
        return None if is_placeholder(text) else text
    kept = []
    for s in _sentences(text):
        m = _SOURCE.search(s)
        if not (m and _GAP.search(s)):
            kept.append(s)
            continue
        # Keep what comes before the clause the note starts in, if that is a
        # real statement on its own.
        cuts = [c for c in _CLAUSE.finditer(s) if c.start() < m.start()]
        if cuts:
            head = s[:cuts[-1].start()].rstrip(' ,;-—–')
            if len(head) >= 25 and not is_placeholder(head):
                kept.append(head + '.')
    out = ' '.join(kept).strip()
    return None if is_placeholder(out) else out


# Investor phrases that describe unnamed backers rather than name them.
_GROUP_NOUN = re.compile(r"\b(?:investors?|backers?|shareholders?|lenders?|individuals|funds|"
                         r"family\s+offices|LPs|limited\s+partners|angels)\b", re.I)
_DESCRIPTORS = {
    'a', 'an', 'the', 'and', 'of', 'with', 'group', 'consortium', 'syndicate',
    'several', 'multiple', 'various', 'other', 'others', 'some', 'certain',
    'undisclosed', 'unnamed', 'unknown', 'unidentified', 'unspecified', 'anonymous',
    'existing', 'new', 'additional', 'previous', 'current', 'returning', 'prior',
    'angel', 'institutional', 'private', 'individual', 'strategic', 'financial',
    'retail', 'family', 'state-linked', 'u.s.-based', 'us-based', 'local',
    'foreign', 'international', 'global', 'european', 'american', 'asian',
    'government', 'industrial', 'sovereign', 'wealth', 'pension', 'high-net-worth',
}


def is_unnamed_group(name):
    """True for "institutional investors", "a group of family offices",
    "Unknown institutional lender" — no actual name in it."""
    if is_placeholder(name):
        return True
    if not _GROUP_NOUN.search(name):
        return False
    words = re.findall(r"[\w.'’-]+", name)
    leftover = [w for w in words
                if not _GROUP_NOUN.fullmatch(w)
                and w.lower() not in _DESCRIPTORS
                and w.lower() not in ('investor', 'backer', 'shareholder', 'lender', 'offices', 'office')]
    # Anything left that looks like a name (capitalised or a number) means a
    # real party is named, e.g. "NSFO Family Office".
    return not any(w[:1].isupper() or w[:1].isdigit() for w in leftover)


def clean_investor_text(text):
    """The investors box as a clean list of named parties, or None.

    "Unknown" -> None;  "Valor and other undisclosed investors" -> "Valor";
    "existing investors including SoftBank" -> "SoftBank".
    """
    from src.utils.investor_parser import parse_investors  # avoid an import cycle
    if is_placeholder(text):
        return None
    names = [f'{name} (lead)' if lead else name for name, lead in parse_investors(text)]
    return ', '.join(names) if names else None
