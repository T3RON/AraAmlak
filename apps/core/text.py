"""
apps/core/text.py — Shared text normalisation utilities.

normalize_fa(text) is the single canonical function used across
the whole platform for:
  - Search / filter (pg_trgm queries)
  - Import deduplication
  - AI intent parsing (Phase 9)
  - Matching engine fuzzy scoring (Phase 3)

Rules applied (in order):
  1. Strip leading/trailing whitespace.
  2. Normalise Arabic Kaf / Yeh → Persian equivalents.
  3. Map Eastern-Arabic / Extended-Arabic-Indic digits → ASCII digits.
  4. Collapse multiple internal whitespace runs to a single space.
  5. Remove zero-width characters (ZWNJ, ZWJ, BOM etc.).
"""

from __future__ import annotations

import re

# Arabic/Persian character pairs to unify
_ARABIC_TO_PERSIAN: dict[str, str] = {
    "\u06af": "\u06af",  # ARABIC LETTER GAF — already correct
    "\u0643": "\u06a9",  # ARABIC LETTER KAF → ARABIC LETTER KEHEH (ك → ک)
    "\u064a": "\u06cc",  # ARABIC LETTER YEH → ARABIC LETTER FARSI YEH (ي → ی)
    "\u0649": "\u06cc",  # ARABIC LETTER ALEF MAKSURA → ی
    "\u0622": "\u0622",  # ARABIC LETTER ALEF WITH MADDA ABOVE — keep
}

# Eastern-Arabic (U+0660–0669) and Extended-Arabic-Indic (U+06F0–06F9) → ASCII
_ARABIC_DIGITS: dict[str, str] = {
    chr(0x0660 + i): str(i) for i in range(10)  # ٠١٢٣٤٥٦٧٨٩
}
_ARABIC_DIGITS.update(
    {chr(0x06F0 + i): str(i) for i in range(10)}  # ۰۱۲۳۴۵۶۷۸۹
)

# Zero-width / invisible characters
_ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\u200e\u200f\ufeff]")

# Multiple spaces (after digit/char normalisation)
_MULTI_SPACE = re.compile(r"\s{2,}")


def normalize_fa(text: str) -> str:
    """
    Return a normalised version of a Persian/Arabic string.

    Idempotent: normalize_fa(normalize_fa(x)) == normalize_fa(x).
    Safe with None — returns empty string.
    """
    if not text:
        return ""
    text = str(text).strip()

    # 1. Remove zero-width characters
    text = _ZERO_WIDTH.sub("", text)

    # 2. Arabic Kaf/Yeh → Persian equivalents
    for arabic, persian in _ARABIC_TO_PERSIAN.items():
        text = text.replace(arabic, persian)

    # 3. Arabic/Indic digits → ASCII digits
    for ar_digit, ascii_digit in _ARABIC_DIGITS.items():
        text = text.replace(ar_digit, ascii_digit)

    # 4. Collapse multiple spaces
    text = _MULTI_SPACE.sub(" ", text)

    return text.strip()


def normalize_phone_ir(phone: str) -> str:
    """
    Normalise an Iranian phone number to the form 09XXXXXXXXX.

    Handles:
      +989...  →  09...
      00989... →  09...
      989...   →  09...
      9...     →  09...  (missing leading zero)

    Returns the normalised string, or the original if it doesn't look
    like an Iranian mobile number.
    """
    if not phone:
        return phone
    p = normalize_fa(phone)
    # Remove spaces/dashes/parentheses
    p = re.sub(r"[\s\-\(\)]", "", p)
    if p.startswith("+98"):
        p = "0" + p[3:]
    elif p.startswith("0098"):
        p = "0" + p[4:]
    elif p.startswith("98") and len(p) == 12:
        p = "0" + p[2:]
    elif p.startswith("9") and len(p) == 10:
        p = "0" + p
    return p
