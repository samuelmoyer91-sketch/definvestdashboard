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
English, German and Czech around 36-40%, French and Italian above 40%. A sentence
is only treated as the start of the scramble if the WHOLE remainder of the
text is vowel-poor too, so one odd line (an acronym list, a byline) never cuts
a real article short.
"""

import re
import unicodedata

VOWELS = set("aeiouy")

# Random letters sit near 0.23 and real prose near 0.36+. 0.29 leaves a wide
# margin on both sides.
SCRAMBLE_THRESHOLD = 0.29

# Ignore scrambled-looking stretches too short to matter.
MIN_SCRAMBLED_LETTERS = 300

# The readable part must look clearly like prose before anything is cut.
MIN_GAP = 0.08

# How far the cut may move to land on a sentence end.
SNAP_WORDS = 5


def _letters(text):
    """Latin letters of `text`, lower-cased, accents removed (é -> e, ü -> u).

    Other scripts are ignored rather than counted: Arabic, Cyrillic or Hebrew
    letters are neither a-z vowels nor consonants, and counting them as
    consonants made an English article ending in Arabic boilerplate look
    scrambled.
    """
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return [c for c in decomposed if "a" <= c <= "z"]


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


def readable_part(text):
    """Return `text` cut at the point where it turns into scrambled letters.

    Text that never turns scrambled comes back unchanged — including text that
    is scrambled from the first word, where there is no readable part to keep
    (the article is then refused and shown in triage for a human to judge).

    The cut is a change point: the split that best separates prose-like text
    before it from random-looking letters after it. Each candidate is scored
    by the between-group sum of squares, n1*n2/n * (share1 - share2)^2, which
    weighs both sides by their size — a plain difference of shares lets a
    short, vowel-rich headline win and cuts the lead off. It works word by
    word because the scramble often begins mid-sentence.
    """
    if not text:
        return text

    words = list(_WORD.finditer(text))
    counts = [_counts(w.group()) for w in words]
    total_vowels = sum(v for v, _ in counts)
    total_letters = sum(n for _, n in counts)
    if total_letters < MIN_SCRAMBLED_LETTERS:
        return text

    best_cut, best_score = None, 0.0
    head_vowels = head_letters = 0
    for k, (vowels, letters) in enumerate(counts):
        tail_vowels = total_vowels - head_vowels
        tail_letters = total_letters - head_letters
        if tail_letters < MIN_SCRAMBLED_LETTERS:
            break
        if head_letters:
            head_share = head_vowels / head_letters
            tail_share = tail_vowels / tail_letters
            if tail_share < SCRAMBLE_THRESHOLD and head_share - tail_share > MIN_GAP:
                score = (head_letters * tail_letters / total_letters
                         * (head_share - tail_share) ** 2)
                if score > best_score:
                    best_cut, best_score = k, score
        head_vowels += vowels
        head_letters += letters

    if best_cut is None:
        return text

    # The change point lands within a few words of the true boundary, and on
    # every sample seen the scramble begins at a sentence start. Snap to the
    # nearest sentence end so the cut neither drops the lead's last words
    # ("with a target of €500m.") nor keeps a scrambled one ("capital.Yv").
    for step in range(SNAP_WORDS + 1):
        for k in (best_cut + step, best_cut - step):
            if 0 < k < len(words) and words[k - 1].group()[-1] in ".!?":
                return text[:words[k].start()].rstrip()
    return text[:words[best_cut].start()].rstrip()
