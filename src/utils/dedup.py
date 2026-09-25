"""
Duplicate-deal detection — shared logic.

Pure functions, no database. Used by BOTH:
  - scripts/find_duplicates.py  (CLI report)
  - src/web/app.py  /duplicates  (triage-app page)

Tune the matching behavior here, in ONE place, and both the command-line
report and the in-app page reflect the change. Nothing here writes to the
database or affects the pipeline — it only analyzes a list of deals.

------------------------------------------------------------------------
TUNING KNOBS
------------------------------------------------------------------------
"""

import re
import unicodedata
from datetime import datetime

WINDOW_DAYS = 30          # Two cards within this many days are dup candidates.
AMOUNT_TOLERANCE = 0.05   # Amounts "match" if within 5% (catches $28M vs $28.5M).

# Legal suffixes / filler stripped when comparing company names. We do NOT
# strip sector words like "aerospace" or "space" — those distinguish real
# companies (GE Aerospace vs GKN Aerospace), so removing them would create
# false merges.
NAME_NOISE = [
    'inc', 'incorporated', 'corp', 'corporation', 'llc', 'ltd', 'limited',
    'co', 'company', 'plc', 'lp', 'holdings', 'group', 'the',
    # European legal forms: "Exail Technologies SA" vs "Exail Technologies"
    'sa', 'ag', 'gmbh', 'mbh', 'nv', 'bv', 'se', 'spa', 'srl', 'sas', 'ab',
    'oy', 'oyj', 'asa', 'kg', 'gruppe',
]

# --- Pair-matching rules (reworked 2026-09-25) -------------------------------
# Measured against 27 hand-verified duplicate pairs, the old rule (identical
# normalized name + amounts within 5% + 30 days) caught 1. See find_pairs.
EXTENDED_WINDOW_DAYS = 60   # same amount and same place: a re-report weeks later
CONVERTED_TOLERANCE = 0.12  # either amount converted from another currency (FX drift)
SAME_AMOUNT = 0.01          # "identical" — lets a buyer-HQ vs target-HQ pair match
MIN_TITLE_SIMILARITY = 0.4  # needed when an amount is missing and the place is unclear
MIN_TITLE_SIMILARITY_SAME_CITY = 0.25  # lowest real same-town pair 0.25 (Heven); a false one 0.20 (Iten)

# Too common in company names to link two records on their own.
_GENERIC_NAME_WORDS = set('''
    defense defence aerospace systems system technologies technology tech industries industrial
    international global space solutions services energy manufacturing security capital
    partners national american advanced labs lab robotics dynamics research center centre
    corp group holdings aero air naval marine motors electronics engineering and of for
    us usa uk new north south east west first united fund ventures venture
'''.split())

# Same company under two names.
_COMPANY_ALIASES = {'rtx': 'raytheon'}

# Words that say nothing about WHICH deal a headline describes.
_TITLE_STOPWORDS = set('''
    a an the of for in on at to and with by from as its into after new
    raises raise raised invests invest investment acquires acquire acquisition buys buy
    opens open builds build expands expand expansion facility plant site factory hub center centre
    deal funding round series seed million billion usd eur gbp announces secures secure
    launches launch plans plan completes complete closes close
'''.split())


# Fixed (approximate) FX rates -> USD. Deliberately simple, not live: a deal
# tracker doesn't need to-the-cent accuracy, and fixed rates keep amounts
# stable/comparable over time. Edit these occasionally if a rate drifts a lot.
# Detection matches the symbol OR the 3-letter code anywhere in the amount text.
FX_RATES = {
    'EUR': 1.08,   # € euro
    'GBP': 1.27,   # £ pound sterling
    'CAD': 0.73,   # C$ Canadian dollar
    'AUD': 0.66,   # A$ Australian dollar
    'JPY': 0.0067, # ¥ yen
    'INR': 0.012,  # ₹ Indian rupee
    'ILS': 0.27,   # ₪ Israeli shekel
}
# Symbol -> currency code. Order matters for C$/A$ before plain $.
FX_SYMBOLS = [('€', 'EUR'), ('£', 'GBP'), ('₪', 'ILS'), ('₹', 'INR'), ('¥', 'JPY')]

_SYM_TO_CODE = {'€': 'EUR', '£': 'GBP', '¥': 'JPY', '₹': 'INR', '₪': 'ILS'}
# Spelled-out currency names (the AI sometimes writes "110 million euros").
_WORD_TO_CODE = {
    'euro': 'EUR', 'euros': 'EUR',
    'pound': 'GBP', 'pounds': 'GBP', 'sterling': 'GBP',
    'yen': 'JPY',
    'shekel': 'ILS', 'shekels': 'ILS',
    'rupee': 'INR', 'rupees': 'INR',
}
# Magnitude words. 'crore' (10M) and 'lakh' (100k) show up in Indian coverage.
_UNITS = {
    'trillion': 1e12, 't': 1e12,
    'billion': 1e9, 'bn': 1e9, 'b': 1e9,
    'million': 1e6, 'mm': 1e6, 'm': 1e6,
    'thousand': 1e3, 'k': 1e3,
    'crore': 1e7, 'lakh': 1e5,
}
_CODES = 'USD|EUR|GBP|CAD|AUD|JPY|INR|ILS'

# One "money mention": optional currency prefix, a number, optional magnitude,
# optional trailing code/word. Deliberately finds EVERY mention in the string so
# dual-currency text ("€450M ($530M)") can be resolved properly rather than
# having the first number blindly paired with whatever symbol appears anywhere.
# Note the prefix code has no trailing \b so glued forms ("EUR1.6B") match.
# The unit and trailing-code groups each carry their own \b INSIDE the optional
# group: a bare \b after an optional group forces the engine to backtrack into
# the number when the next token isn't a known unit, silently truncating it
# ("$1.25T" -> 1.0). Longest alternatives come first so "million" isn't matched
# as "m" with "illion" left over.
_MONEY_RE = re.compile(
    r'(?P<pre>US\$|C\$|A\$|[€£¥₹₪$]|\b(?:' + _CODES + r'))?'
    r'\s*(?P<num>\d[\d,]*(?:\.\d+)?)'
    r'(?:\s*(?P<unit>trillion|billion|million|thousand|crore|lakh|bn|mm|b|m|k|t)\b)?'
    r'(?:\s*(?P<post>\b(?:' + _CODES + r')\b|euros?|pounds?|sterling|yen|shekels?|rupees?))?',
    re.I,
)
# -------------------------------------------------------------------------


def _code_from_match(m):
    """Resolve the currency of a single money mention."""
    pre = (m.group('pre') or '').strip()
    post = (m.group('post') or '').strip().lower()
    # A trailing code or word wins: "$21M CAD" is Canadian, "110 million euros"
    # is euros, regardless of what the prefix looked like.
    if post:
        if post.upper() == 'USD' or post.upper() in FX_RATES:
            return post.upper()
        if post in _WORD_TO_CODE:
            return _WORD_TO_CODE[post]
    if pre:
        up = pre.upper()
        if up == 'US$':
            return 'USD'
        if up == 'C$':
            return 'CAD'
        if up == 'A$':
            return 'AUD'
        if pre in _SYM_TO_CODE:
            return _SYM_TO_CODE[pre]
        if pre == '$':
            return 'USD'
        if up == 'USD' or up in FX_RATES:
            return up
    return 'USD'


def _money_mentions(text):
    """Every (currency_code, native_value) money mention in the text, in order."""
    out = []
    for m in _MONEY_RE.finditer(str(text)):
        try:
            val = float(m.group('num').replace(',', ''))
        except ValueError:
            continue
        unit = (m.group('unit') or '').lower()
        if unit:
            val *= _UNITS[unit]
        out.append((_code_from_match(m), val))
    return out


def normalize_company(name):
    """Lowercase, strip punctuation and legal suffixes for comparison."""
    if not name:
        return ''
    s = name.lower().replace('&amp;', '&')
    s = re.sub(r'[^\w\s]', ' ', s)
    words = [w for w in s.split() if w not in NAME_NOISE]
    return ' '.join(words).strip()


def detect_currency(amount):
    """Return the currency the amount is WRITTEN in, defaulting to USD.

    This is the currency of the first money mention, i.e. how the deal is
    denominated -- "€450M ($530M)" is a euro amount with a dollar gloss, so
    this returns EUR. Handles symbols (€ £ ₪ ₹ ¥), US$/C$/A$, 3-letter codes
    both spaced and glued ("EUR 6M", "EUR1.6B"), and spelled-out names
    ("110 million euros"). Plain '$' / no marker = USD.
    """
    if not amount:
        return 'USD'
    mentions = _money_mentions(amount)
    return mentions[0][0] if mentions else 'USD'


def parse_amount(amount, convert=True):
    """Parse a deal-amount string into USD dollars (float), or None.

    Handles "$28,500,000", "$2M", "$1.3B", "250,000,000", "£19M", "€110M",
    "EUR1.6B", "110 million euros", "₹100 crore", and dual-currency strings
    like "€450M ($530M)" or "$21M CAD ($15.2M USD)".

    Non-USD amounts are converted using the fixed FX_RATES table, EXCEPT when
    the text states its own USD equivalent -- see below. Pass convert=False to
    get the raw magnitude as written, without FX conversion.
    """
    if not amount:
        return None
    mentions = _money_mentions(amount)
    if not mentions:
        return None

    code, val = mentions[0]
    if not convert or code == 'USD':
        return val

    converted = val * FX_RATES.get(code, 1.0)

    # If the text also quotes its own USD figure for the same amount (e.g.
    # "€450M ($530M)"), prefer it: that's the real rate on the deal date, which
    # beats our fixed table. Only trust it when it's in the same ballpark as our
    # own conversion, so an unrelated dollar figure quoted alongside (say, a
    # valuation next to a euro round) can't hijack the amount.
    if converted:
        for other_code, other_val in mentions[1:]:
            if other_code == 'USD' and abs(other_val - converted) / converted <= 0.5:
                return other_val
    return converted


def amounts_match(a, b, tolerance=AMOUNT_TOLERANCE):
    """True if two parsed amounts are within tolerance, or both missing."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if a == 0 or b == 0:
        return a == b
    return abs(a - b) / max(a, b) <= tolerance


def fmt_amount(val):
    if val is None:
        return '(no $)'
    if val >= 1_000_000_000_000:
        return f'${val/1_000_000_000_000:.2f}T'
    if val >= 1_000_000_000:
        return f'${val/1_000_000_000:.2f}B'
    if val >= 1_000_000:
        return f'${val/1_000_000:.1f}M'
    return f'${val:,.0f}'


def same_group(a, b):
    """True when two entries are deliberate passes over the SAME article.

    A roundup article is re-extracted once per deal it contains, so its passes
    share a company and a publication date by construction — and when neither
    deal states a figure, amounts_match(None, None) is True. That is exactly
    the signature below treats as a duplicate, so without this the split deals
    would flag each other and be routed out of the triage queue.

    Deliberately NOT fixed by changing amounts_match: two sources covering one
    undisclosed round is a real duplicate worth catching, and that is the same
    (None, None) case.

    Entries with no group_key (the default) never match, so this is inert for
    any caller that does not set one.
    """
    return a.get('group_key') is not None and a.get('group_key') == b.get('group_key')


# --- Pair matching ------------------------------------------------------------

_US_STATE_NAMES = set('''alabama alaska arizona arkansas california colorado connecticut delaware
    florida georgia hawaii idaho illinois indiana iowa kansas kentucky louisiana maine maryland
    massachusetts michigan minnesota mississippi missouri montana nebraska nevada ohio oklahoma
    oregon pennsylvania tennessee texas utah vermont virginia washington wisconsin wyoming'''.split()) | {
    'new hampshire', 'new jersey', 'new mexico', 'new york', 'north carolina', 'north dakota',
    'rhode island', 'south carolina', 'south dakota', 'west virginia', 'district of columbia'}
_US_STATE_ABBR = set('''al ak az ar ca co ct de fl ga hi id il in ia ks ky la me md ma mi mn ms mo
    mt ne nv nh nj nm ny nc nd oh ok or pa ri sc sd tn tx ut vt va wa wv wi wy dc'''.split())
_COUNTRY_SYNONYMS = {
    'uk': 'united kingdom', 'u k': 'united kingdom', 'england': 'united kingdom',
    'scotland': 'united kingdom', 'wales': 'united kingdom', 'great britain': 'united kingdom',
    'usa': 'united states', 'us': 'united states', 'u s': 'united states', 'u s a': 'united states',
    'czechia': 'czech republic', 'turkiye': 'turkey',
}
_PLACEHOLDERS = {'unknown', 'n a', 'na', 'none', 'not specified', 'various', 'multiple locations'}


def _fold(s):
    """Lower-case and strip accents: 'Osnabrück' -> 'osnabruck'."""
    return unicodedata.normalize('NFKD', (s or '').lower()).encode('ascii', 'ignore').decode()


def _name_tokens(norm):
    return frozenset(_COMPANY_ALIASES.get(t, t) for t in _fold(norm).split())


def _one_edit_apart(a, b):
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def same_company(a_norm, b_norm):
    """Two normalized company names that plausibly name the same company.

    Equal word sets, or one name's words all appearing in the other ("Stoke
    Space" / "Stoke Space Technologies", "Raytheon" / "Raytheon RTX"), or a
    one-letter typo in the first word with the rest equal ("Erail" / "Exail").
    The shorter name must contain a distinctive word, so a stray "Aerospace"
    can't match every aerospace company.
    """
    A, B = _name_tokens(a_norm), _name_tokens(b_norm)
    if not A or not B:
        return False
    if A == B:
        return True
    small = A if len(A) < len(B) else B
    if (A <= B or B <= A) and small - _GENERIC_NAME_WORDS:
        return True
    fa, fb = _fold(a_norm).split()[0], _fold(b_norm).split()[0]
    return (len(fa) >= 5 and len(fb) >= 5 and _one_edit_apart(fa, fb)
            and A - {_COMPANY_ALIASES.get(fa, fa)} == B - {_COMPANY_ALIASES.get(fb, fb)})


def _place(location):
    """(city, country) from a "City, ST, Country"-style string; either may be None."""
    parts = [re.sub(r'[^a-z0-9 ]', ' ', _fold(p)).strip() for p in (location or '').split(',')]
    parts = [re.sub(r'\s+', ' ', p) for p in parts if p]
    if not parts or parts[0] in _PLACEHOLDERS or parts[0].startswith('multiple'):
        return None, None
    last = parts[-1]
    country = _COUNTRY_SYNONYMS.get(last, last)
    if last in _US_STATE_ABBR or last in _US_STATE_NAMES:
        country = 'united states'
    city = parts[0] if len(parts) >= 2 else None
    # "Colorado, USA" names a state, not a city. (Three-part strings keep their
    # first part: "New York, NY, USA" and "Washington, DC, USA" are cities.)
    if city and len(parts) == 2 and (city in _US_STATE_NAMES or city in _US_STATE_ABBR):
        city = None
    return city, country


def _same_place(a_loc, b_loc):
    """'same', 'different', or 'unknown' — whether two locations agree."""
    ca, na = _place(a_loc)
    cb, nb = _place(b_loc)
    if na and nb and na != nb:
        return 'different'
    if ca and cb:
        if ca == cb:
            return 'same'
        # One names a region the other sits in: "Saxony, Germany" vs "Leipzig, Saxony, Germany"
        if ca in _fold(b_loc) or cb in _fold(a_loc):
            return 'unknown'
        return 'different'
    return 'unknown'


def _title_words(title, exclude):
    words = set()
    for w in re.findall(r'[a-z0-9]+', _fold(title)):
        if len(w) < 3 or w in _TITLE_STOPWORDS or w in exclude or re.fullmatch(r'\d+[kmb]?', w):
            continue
        words.add(w[:5])  # crude stem: "expands"/"expansion", "invests"/"investment"
    return words


def title_similarity(a, b):
    """Share of meaningful headline words two records have in common (0-1).

    Both companies' own name words are left out, so two "Northrop Grumman
    builds…" headlines are not similar just for naming the same company.
    """
    exclude = _name_tokens(a['norm']) | _name_tokens(b['norm'])
    A, B = _title_words(a.get('title'), exclude), _title_words(b.get('title'), exclude)
    return len(A & B) / len(A | B) if A and B else 0.0


def _converted(raw):
    return bool(raw) and detect_currency(raw) != 'USD'


def match_pair(a, b, window_days=WINDOW_DAYS, tolerance=AMOUNT_TOLERANCE):
    """Day gap if two enriched records look like the same deal, else None.

    - Different city or country means a different deal, unless the amounts
      are identical (a buyer and its target reported from their own HQs).
    - Amounts within 5%, or 12% when either was converted from another
      currency (FX drift: "€1B" vs "$1.16B"); 60 days instead of 30 when the
      place agrees too (a deal re-reported weeks later).
    - With an amount missing on either side, the place must agree and the
      headlines must be similar. The old rule matched any two no-amount cards
      from one company, e.g. Northrop's Utah and Florida sites.
    """
    if same_group(a, b) or not same_company(a['norm'], b['norm']):
        return None
    if not (a['date'] and b['date']):
        return None
    gap = abs((a['date'] - b['date']).days)
    place = _same_place(a.get('location'), b.get('location'))
    xa, xb = a['amount_num'], b['amount_num']
    if xa and xb:
        diff = abs(xa - xb) / max(xa, xb)
        if diff <= SAME_AMOUNT:
            # Round figures recur ($100M), so the 60-day window needs more than
            # the amount: the same place, or an unclear place plus a similar
            # headline. Without this, four RTX "$100M" cards chained together
            # over three months through one card located only as "USA".
            extended = place == 'same' or (
                place == 'unknown' and title_similarity(a, b) >= MIN_TITLE_SIMILARITY_SAME_CITY)
            return gap if gap <= (EXTENDED_WINDOW_DAYS if extended else window_days) else None
        if place == 'different':
            return None
        tol = CONVERTED_TOLERANCE if (_converted(a.get('amount_raw')) or _converted(b.get('amount_raw'))) else tolerance
        if diff <= tol:
            return gap if gap <= (EXTENDED_WINDOW_DAYS if place == 'same' else window_days) else None
        # Two reports of one deal can disagree on the figure ($3.1M vs $3.4M)
        if (diff <= CONVERTED_TOLERANCE and place == 'same' and gap <= window_days
                and title_similarity(a, b) >= MIN_TITLE_SIMILARITY):
            return gap
        return None
    if place == 'different' or gap > window_days:
        return None
    needed = MIN_TITLE_SIMILARITY_SAME_CITY if place == 'same' else MIN_TITLE_SIMILARITY
    return gap if title_similarity(a, b) >= needed else None


def find_pairs(recs, window_days=WINDOW_DAYS, tolerance=AMOUNT_TOLERANCE,
               dismissed=None, involving=None):
    """(i, j, gap) for every pair of records that look like the same deal.

    Only plausible pairs are examined: records sharing a distinctive company
    word, plus records with identical amounts (typo'd names share no word).
    `dismissed` holds frozenset({id_a, id_b}) pairs Sam marked "not a
    duplicate"; `involving`, if given, restricts results to pairs touching
    those record indices (the triage bucket only cares about queue items).
    """
    buckets = {}
    for i, r in enumerate(recs):
        for t in _name_tokens(r['norm']):
            if len(t) >= 3 and t not in _GENERIC_NAME_WORDS:
                buckets.setdefault(t, []).append(i)
    candidates = set()
    for idxs in buckets.values():
        for x in range(len(idxs)):
            for y in range(x + 1, len(idxs)):
                candidates.add((idxs[x], idxs[y]))
    by_amount = sorted((r['amount_num'], i) for i, r in enumerate(recs) if r['amount_num'])
    for k, (amt, i) in enumerate(by_amount):
        for amt2, j in by_amount[k + 1:]:
            if amt2 > amt * (1 + SAME_AMOUNT):
                break
            candidates.add((min(i, j), max(i, j)))

    pairs = []
    for i, j in candidates:
        if involving is not None and i not in involving and j not in involving:
            continue
        a, b = recs[i], recs[j]
        if dismissed and frozenset((a['id'], b['id'])) in dismissed:
            continue
        gap = match_pair(a, b, window_days, tolerance)
        if gap is not None:
            pairs.append((i, j, gap))
    return pairs


def _components(n, pairs):
    """Union-find: lists of record indices connected by at least one pair."""
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j, _ in pairs:
        parent[find(i)] = find(j)
    comps = {}
    for i, j, _ in pairs:
        comps.setdefault(find(i), set()).update((i, j))
    return [sorted(c) for c in comps.values()]


def find_clusters(deals, window_days=WINDOW_DAYS, tolerance=AMOUNT_TOLERANCE,
                  dismissed=None):
    """Group published deals into duplicate clusters.

    Args:
        deals: list of dicts, each with keys:
            id, company, amount (raw string or None), date (datetime or None),
            title, source, location, and optionally group_key
        window_days: max day-gap for two cards to be a dup pair
        tolerance: amount match tolerance (fraction)
        dismissed: set of frozenset({id_a, id_b}) pairs marked "not a duplicate"

    Returns dict with:
        likely:   clusters containing >= 1 matching pair (see match_pair)
        distinct: multi-card same-company groups with NO matching pair
        overcount: estimated double-counted dollars across likely-dup pairs

    Each cluster is a dict:
        company, entries (sorted by date), pairs (list of (a,b,gap)),
        flagged_ids (set of ids in >=1 pair)
    Nothing is mutated; input deals are read only.
    """
    recs = []
    for d in deals:
        recs.append({
            'id': d.get('id'),
            'company': d.get('company') or d.get('title') or '(unknown)',
            'norm': normalize_company(d.get('company') or d.get('title')),
            'amount_num': parse_amount(d.get('amount')),
            'amount_raw': d.get('amount'),
            'date': d.get('date'),
            'title': d.get('title') or d.get('company') or '',
            'source': d.get('source') or '',
            'location': d.get('location') or '',
            'group_key': d.get('group_key'),
        })

    pairs = find_pairs(recs, window_days, tolerance, dismissed=dismissed)

    likely, overcount = [], 0.0
    in_pair = set()
    for comp in _components(len(recs), pairs):
        members = set(comp)
        entries = sorted((recs[i] for i in comp), key=lambda x: x['date'] or datetime.min)
        cpairs = [(recs[i], recs[j], gap) for i, j, gap in pairs if i in members]
        flagged = {r['id'] for r in entries}
        in_pair |= members
        for a, b, _ in cpairs:
            amts = [x for x in (a['amount_num'], b['amount_num']) if x]
            overcount += min(amts) if amts else 0
        likely.append({'company': entries[0]['company'], 'entries': entries,
                       'pairs': cpairs, 'flagged_ids': flagged})

    # Same-company groups with no matching pair, for a manual look.
    groups = {}
    for i, r in enumerate(recs):
        if r['norm'] and i not in in_pair:
            groups.setdefault(r['norm'], []).append(r)
    distinct = [{'company': e[0]['company'],
                 'entries': sorted(e, key=lambda x: x['date'] or datetime.min),
                 'pairs': [], 'flagged_ids': set()}
                for e in groups.values() if len(e) > 1]

    likely.sort(key=lambda c: -len(c['pairs']))
    distinct.sort(key=lambda c: -len(c['entries']))
    return {'likely': likely, 'distinct': distinct, 'overcount': overcount}


def _match_reason(group_entries, max_gap):
    """Human-readable why-flagged string, e.g. 'same company · ~$28.5M · within 8 days'."""
    parts = ['same company']
    amts = [e['amount_num'] for e in group_entries if e['amount_num']]
    if amts:
        parts.append('~' + fmt_amount(min(amts)))
    else:
        parts.append('no $ amount')
    if max_gap >= 9999:
        parts.append('date unknown')
    elif max_gap == 0:
        parts.append('same day')
    else:
        parts.append(f'within {max_gap} days')
    return ' · '.join(parts)


# --- Source ranking: pick the "best" item to keep in a duplicate cluster ----
# A "Direct:"-prefixed feed pulls straight from a publisher's own RSS, so the
# article scrapes cleanly; everything else is a Google News keyword/entity
# search that arrives via a Google redirect (often a poor scrape). Among
# sources, editorial trade press usually carries a fuller writeup than a raw
# press-release wire. This is the same feed-quality logic behind the direct-
# feed migration, applied to choose which duplicate to keep.
_TRADE_PRESS = (
    'spacenews', 'breaking defense', 'defense news', 'defensescoop',
    'defense one', 'war zone', 'pulse 2.0', 'techcrunch', 'axios',
    'bloomberg', 'reuters', 'wall street journal', 'financial times',
)


def _is_direct_source(source):
    """True if the item came from a direct-publisher feed (vs a Google search)."""
    return str(source or '').strip().lower().startswith('direct:')


def _is_trade_press(source):
    """True if the feed source names an editorial outlet (vs a newswire)."""
    s = str(source or '').lower()
    return any(name in s for name in _TRADE_PRESS)


def _source_sort_key(item):
    """Sort key that ranks a cluster's items best-first.

    Priority (each tier breaks ties for the previous one):
      1. Direct-publisher feed over Google News
      2. Has a dollar amount extracted
      3. Trade press / major outlet over raw newswire
      4. Earliest date (first to report); undated items last
    Smaller tuple sorts first, so each field is 0 for the preferred case.
    """
    return (
        0 if _is_direct_source(item.get('source')) else 1,
        0 if item.get('amount_num') is not None else 1,
        0 if _is_trade_press(item.get('source')) else 1,
        item.get('date') or datetime.max,
    )
# ----------------------------------------------------------------------------


def find_queue_duplicates(queue_items, published_items,
                          window_days=WINDOW_DAYS, tolerance=AMOUNT_TOLERANCE):
    """Flag triage-queue items that look like duplicates of an already-published
    deal OR of another queue item, BEFORE Sam triages them.

    READ-ONLY / pure: computes from data passed in, mutates nothing, no DB.

    Args:
        queue_items:     list of dicts (id, company, amount, date, title, source,
                         location, insight) — items currently awaiting triage.
        published_items: same shape — deals already on the dashboard (master_list).
        window_days, tolerance: matching thresholds (defaults from this module).

    Returns dict:
        groups:        list of deal-groups, each a dict:
                          type: 'matches_published' | 'queue_only'
                          company: display name
                          reason: human match-reason string
                          confidence: float (higher = more certain; for sorting)
                          published: list of published entries (Type 1 anchors; [] for Type 2)
                          queue: list of queue entries (actionable; the dup candidates)
        flagged_ids:   set of queue-item ids that appear in any group
                       (these are the ones home() should pull OUT of the main queue)

    Only queue items that match something are flagged. A queue item that
    matches nothing stays in the normal triage flow (not returned here).
    """
    def enrich(d, origin):
        return {
            'id': d.get('id'),
            'origin': origin,
            'company': d.get('company') or d.get('title') or '(unknown)',
            'norm': normalize_company(d.get('company') or d.get('title')),
            'amount_num': parse_amount(d.get('amount')),
            'amount_raw': d.get('amount'),
            'date': d.get('date'),
            'title': d.get('title') or d.get('company') or '',
            'source': d.get('source') or '',
            'location': d.get('location') or '',
            'insight': d.get('insight') or '',
            'group_key': d.get('group_key'),
        }

    recs = [enrich(d, 'queue') for d in queue_items] + \
           [enrich(d, 'published') for d in published_items]

    # Pairs are found by the shared rules (match_pair), but only pairs that
    # touch a queue item: published-vs-published duplicates are the Published
    # Dup Check's job, and skipping them keeps the triage page load cheap.
    n_queue = len(queue_items)
    pairs = find_pairs(recs, window_days, tolerance, involving=set(range(n_queue)))

    groups, flagged_ids = [], set()
    if pairs:
        comps = {k: [recs[i] for i in comp]
                 for k, comp in enumerate(_components(len(recs), pairs))}
        for root, members in comps.items():
            if len(members) < 2:
                continue
            q = [m for m in members if m['origin'] == 'queue']
            pub = [m for m in members if m['origin'] == 'published']
            # a group is only actionable if it contains a queue item to act on
            if not q:
                continue
            # max gap among members that actually have dates
            dated = [m['date'] for m in members if m['date']]
            max_gap = (max((d2 - d1).days for d1 in dated for d2 in dated)
                       if len(dated) > 1 else 9999)
            amts = [m['amount_num'] for m in members if m['amount_num']]
            has_amount = len(amts) > 0
            tight = max_gap <= 10
            gtype = 'matches_published' if pub else 'queue_only'
            # confidence: published match + dollar amount + tight window = highest
            confidence = (
                (2.0 if pub else 0.0)
                + (1.0 if has_amount else 0.0)
                + (1.0 if tight else 0.0)
            )
            # Rank the queue items best-source-first so the group's default
            # "keep" pick (and the table order) is a real recommendation, not
            # just the oldest item. See _source_sort_key.
            q.sort(key=_source_sort_key)
            pub.sort(key=lambda x: x['date'] or datetime.min)
            for m in q:
                flagged_ids.add(m['id'])
            groups.append({
                'type': gtype,
                'company': members[0]['company'],
                'reason': _match_reason(members, max_gap),
                'confidence': confidence,
                'published': pub,
                'queue': q,
            })

    # highest confidence first; matches-published above queue-only at equal confidence
    groups.sort(key=lambda g: (-g['confidence'], 0 if g['type'] == 'matches_published' else 1))
    return {'groups': groups, 'flagged_ids': flagged_ids}
