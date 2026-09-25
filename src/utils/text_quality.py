"""
Detect paywall-scrambled article text and keep only the readable part.

Created 2026-09-24. Sifted serves non-subscribers a readable headline and
first paragraph, then replaces the rest of the article with letter-scrambled
text of the same shape:

    ...has raised a $25.5m seed round to develop a new architecture for
    quantum chips.Plf zahss fmk hvf ud Xbyqwjtblrda, r Hvyik-kfgah TV...

Sent as-is, the model's safety filter reads the cipher-like text as a possible
attempt to smuggle something past it and refuses (stop_reason=refusal,
category=bio). Every Sifted article failed this way, and a refused article was
hidden from triage. The readable lead nearly always states the deal, so
trimming at the scramble is enough to extract it.

How scrambled text is recognised: random letters are ~23% vowels (a e i o u y
out of 26). Real prose in every language the feeds carry sits far higher:
English, German and Czech around 36-40%, French and Italian above 40%.

The scramble does not always run to the end: many Sifted pages follow it with
readable "related articles" teasers. So the first step looks for the first
stretch of text that is random-looking throughout — over 1,669 real articles
no 300-letter stretch fell below 25% vowels, while every scrambled stretch sat
at 16-22% — and the second step finds exactly where that stretch begins.
Everything from there on is dropped, teasers included.
"""

import re
import unicodedata

VOWELS = set("aeiouy")

# Random letters sit near 0.23 and real prose near 0.36+. 0.29 leaves a wide
# margin on both sides.
SCRAMBLE_THRESHOLD = 0.29

# Ignore scrambled-looking stretches too short to matter.
MIN_SCRAMBLED_LETTERS = 300

# A stretch of WINDOW_LETTERS letters with a vowel share under WINDOW_THRESHOLD
# is taken as the start of a scrambled run. Measured 2026-09-24: the lowest
# such share in 1,669 real articles was 0.253 (a boilerplate-heavy local news
# page); scrambled stretches were 0.16-0.22.
WINDOW_LETTERS = 300
WINDOW_THRESHOLD = 0.235

# The readable part must look clearly like prose before anything is cut.
MIN_GAP = 0.08

# How far the cut may move to land on a sentence end.
SNAP_WORDS = 5

# Letter pairs that almost never occur in English, German or French: fewer
# than 2 in 100,000 pairs across 1,669 stored and live articles (2026-09-24).
# Scrambled text is full of them — over half its words contain one, against
# at most 8% in real articles. Used only to place the cut precisely once a
# scramble has already been found by vowel share: the pairs are common in
# Polish and Czech (cz, rz, zb), so they must not decide on their own.
RARE_PAIRS = frozenset("""
bf bg bk bq bv bx bz cj cv cw cx cz dk dx dz fh fj fn fq fv fw fx fz gj
gq gv gw gx gz hj hx hz jb jc jd jg jh jj jk jl jm jn jq jr js jt jv jw
jx jy jz kd kg kj kq kv kw kx kz lj lq lx lz mj mq mw mx mz nx oq pj pk
pn pq pv pw px pz qb qc qd qe qf qg qh qi qj qk ql qm qn qo qp qq qr qs
qt qv qw qx qy qz rj rq rx sx sz tj tq uj uq uu uw vb vd vf vg vh vj vk
vl vm vn vp vq vv vw vx vz wg wj wq wv wx wz xb xd xf xg xh xj xk xl xm
xn xq xr xv xw xx xy xz yj yk yq yv yx yy zb zc zd zf zg zh zj zk zl zm
zn zp zq zr zs zt zv zw zx zy
""".split())

# Placing the cut: the boundary is searched within this many words before the
# point where vowel share first flagged the scramble (it can flag late when the
# scramble opens with vowel-rich scrambled names).
LOCAL_WORDS = 150


def _letters(text):
    """Latin letters of `text`, lower-cased, accents removed (é -> e, ü -> u).

    Other scripts are ignored rather than counted: Arabic, Cyrillic or Hebrew
    letters are neither a-z vowels nor consonants, and counting them as
    consonants made an English article ending in Arabic boilerplate look
    scrambled.
    """
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return [c for c in decomposed if "a" <= c <= "z"]


def _is_odd(word):
    """True if a word of 3+ Latin letters contains a RARE_PAIRS letter pair."""
    letters = "".join(_letters(word))
    return len(letters) >= 3 and any(letters[i:i + 2] in RARE_PAIRS
                                     for i in range(len(letters) - 1))


def _odd_change_point(words, lo, hi):
    """Word index in (lo, hi) where rare letter pairs switch on, or None.

    Same size-weighted change point as the vowel search, over one flag per
    word of 3+ letters: does it contain a RARE_PAIRS pair? Readable English
    has almost none; about half of scrambled words have one.
    """
    flags = [(_is_odd(w.group()) if len(_letters(w.group())) >= 3 else None)
             for w in words[lo:hi]]
    eligible = [0]
    odd = [0]
    for f in flags:
        eligible.append(eligible[-1] + (f is not None))
        odd.append(odd[-1] + bool(f))
    n = len(flags)
    best, best_score = None, 0.0
    for p in range(1, n):
        head_n, tail_n = eligible[p], eligible[n] - eligible[p]
        if head_n < 3 or tail_n < 10:
            continue
        head = odd[p] / head_n
        tail = (odd[n] - odd[p]) / tail_n
        if tail >= 0.35 and tail - head >= 0.25:
            score = head_n * tail_n / (head_n + tail_n) * (tail - head) ** 2
            if score > best_score:
                best, best_score = lo + p, score
    return best


def _counts(text):
    letters = _letters(text)
    return sum(c in VOWELS for c in letters), len(letters)


def vowel_share(text):
    vowels, letters = _counts(text)
    return vowels / letters if letters else 1.0


# Words, with a sentence stop split from a capital glued onto it, so
# "approaches.Plf" yields "approaches." and "Plf" — Sifted runs the readable
# lead straight into the scramble without a space.
_WORD = re.compile(r"[^\s.!?]*[.!?]+|[^\s.!?]+")


def _first_scrambled_run(counts, pv, pl):
    """(start, end) word indices of the first random-looking run, or None.

    The run starts at the first WINDOW_LETTERS-letter window under
    WINDOW_THRESHOLD and extends while the windows stay under
    SCRAMBLE_THRESHOLD. `pv`/`pl` are prefix sums of vowels/letters.
    """
    n = len(counts)
    j = 0
    start = end = None
    for i in range(n):
        while j < n and pl[j] - pl[i] < WINDOW_LETTERS:
            j += 1
        letters = pl[j] - pl[i]
        if letters < WINDOW_LETTERS:
            break
        share = (pv[j] - pv[i]) / letters
        if start is None:
            if share < WINDOW_THRESHOLD:
                start, end = i, j
        elif share < SCRAMBLE_THRESHOLD:
            end = j
        else:
            break
    return None if start is None else (start, end)


def _vowel_change_point(pv, pl, end):
    """Fallback cut from vowel share alone, over words [0, end): the split that
    best separates prose-like text from random letters (size-weighted)."""
    best, best_score = None, 0.0
    for k in range(1, end):
        head_letters, tail_letters = pl[k], pl[end] - pl[k]
        if tail_letters < MIN_SCRAMBLED_LETTERS:
            break
        if not head_letters:
            continue
        head_share = pv[k] / head_letters
        tail_share = (pv[end] - pv[k]) / tail_letters
        if tail_share < SCRAMBLE_THRESHOLD and head_share - tail_share > MIN_GAP:
            score = (head_letters * tail_letters / pl[end]
                     * (head_share - tail_share) ** 2)
            if score > best_score:
                best, best_score = k, score
    return best


def readable_part(text):
    """Return `text` cut where it turns into scrambled letters.

    Text with no scrambled run comes back unchanged. Text scrambled from the
    first word comes back as "" — the caller still has the title, which for a
    funding story usually names the company and the amount.

    Two steps, each with the signal suited to it:
    1. Whether there is a scramble at all: vowel share, which works in every
       language (see _first_scrambled_run). It never fired on 1,669 real
       articles.
    2. Where exactly it begins: rare letter pairs, word by word, searched
       around the point step 1 flagged (_odd_change_point). Vowel share
       alone placed the cut late when the scramble opened with vowel-rich
       scrambled names, and the scramble often starts mid-sentence. Vowel
       share is the fallback if no clear switch in rare pairs is found.
    """
    if not text:
        return text

    words = list(_WORD.finditer(text))
    counts = [_counts(w.group()) for w in words]
    pv, pl = [0], [0]
    for vowels, letters in counts:
        pv.append(pv[-1] + vowels)
        pl.append(pl[-1] + letters)

    run = _first_scrambled_run(counts, pv, pl)
    if run is None:
        return text
    start, end = run
    if start == 0:
        return ""

    cut = _odd_change_point(words, max(0, start - LOCAL_WORDS), end)
    if cut is None:
        cut = _vowel_change_point(pv, pl, end) or start

    # On every sample seen the scramble begins at a sentence start, so snap to
    # a nearby sentence end: forward only over words with no rare pair (so a
    # cut never re-admits scrambled words), backward over anything (dropping
    # a few readable words is harmless).
    for step in range(SNAP_WORDS + 1):
        fwd, back = cut + step, cut - step
        if (fwd < len(words) and words[fwd - 1].group()[-1] in ".!?"
                and not any(_is_odd(w.group()) for w in words[cut:fwd])):
            cut = fwd
            break
        if back > 0 and words[back - 1].group()[-1] in ".!?":
            cut = back
            break
    return text[:words[cut].start()].rstrip() if cut else ""
