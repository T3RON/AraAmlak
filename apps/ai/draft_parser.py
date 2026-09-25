"""
Persian transcript → listing draft parser — Phase 5B.

`parse_listing_transcript(text)` is a **pure function**: no DB, no settings.
It normalises the transcript (`normalize_fa`), extracts structured listing
fields with Persian regexes/word-numbers, and reports which key fields are
missing plus a confidence score.

The extracted `data` dict maps Listing field names to values:
- prices are integer Tomans (میلیارد → 1e9, میلیون → 1e6)
- build_year is Gregorian (شمسی − 621)
- `district` stays plain text; the service layer resolves it to a
  Neighborhood FK (needs DB access, so it is out of scope here)
"""

from __future__ import annotations

import re

from apps.core.text import normalize_fa

# ─── Word numbers ─────────────────────────────────────────────────────────────

_WORD_NUMS: dict[str, int] = {
    "صفر": 0,
    "یک": 1,
    "اول": 1,
    "یکم": 1,
    "دو": 2,
    "دوم": 2,
    "سه": 3,
    "سوم": 3,
    "چهار": 4,
    "چهارم": 4,
    "پنج": 5,
    "پنجم": 5,
    "شش": 6,
    "ششم": 6,
    "شیش": 6,
    "هفت": 7,
    "هفتم": 7,
    "هشت": 8,
    "هشتم": 8,
    "نه": 9,
    "نهم": 9,
    "ده": 10,
    "دهم": 10,
    "یازده": 11,
    "دوازده": 12,
    "سیزده": 13,
    "چهارده": 14,
    "پانزده": 15,
    "پانزدهم": 15,
    "شانزده": 16,
    "هفده": 17,
    "هجده": 18,
    "نوزده": 19,
    "بیست": 20,
}

_PRICE_WORDS: dict[str, int] = {
    **_WORD_NUMS,
    "سی": 30,
    "چهل": 40,
    "پنجاه": 50,
    "شصت": 60,
    "هفتاد": 70,
    "هشتاد": 80,
    "نود": 90,
    "نو": 90,
    "صد": 100,
    "یکصد": 100,
    "دویست": 200,
    "سیصد": 300,
    "چهارصد": 400,
    "پانصد": 500,
}

# Compound word-numbers like "دویست و پنجاه" are handled by joining on " و "
# before lookup: parts are summed (e.g. دویست و پنجاه → 250).


def _word_to_num(token: str, table: dict[str, int] | None = None) -> int | None:
    """Convert a Persian word number (possibly 'X و Y') to an int, or None."""
    table = table or _WORD_NUMS
    token = token.strip()
    if not token:
        return None
    total = 0
    matched = False
    for part in token.split(" و "):
        part = part.strip()
        if part not in table:
            return None
        total += table[part]
        matched = True
    return total if matched else None


# ─── Keyword maps ─────────────────────────────────────────────────────────────

_PROPERTY_TYPE_KEYWORDS: list[tuple[str, str]] = [
    ("آپارتمان", "apartment"),
    ("ویلایی", "villa"),
    ("ویلا", "villa"),
    ("خانه ویلایی", "villa"),
    ("زمین", "land"),
    ("کلنگی", "land"),
    ("باغ", "land"),
    ("مغازه", "commercial"),
    ("غرفه", "commercial"),
    ("دفتر کار", "office"),
    ("اداری", "office"),
    ("دفتر", "office"),
    ("انبار", "warehouse"),
    ("سوله", "warehouse"),
]

_DIRECTION_KEYWORDS: list[tuple[str, str]] = [
    ("شمال شرقی", "north_east"),
    ("شمالغرب", "north_west"),
    ("شمال غربی", "north_west"),
    ("جنوب شرقی", "south_east"),
    ("جنوبغرب", "south_west"),
    ("جنوب غربی", "south_west"),
    ("شمالی", "north"),
    ("جنوبی", "south"),
    ("شرقی", "east"),
    ("غربی", "west"),
]

_AMENITY_KEYWORDS: dict[str, str] = {
    "parking": "پارکینگ",
    "elevator": "آسانسور",
    "storage": "انباری",
    "balcony": "بالکن",
}

# Price multipliers → integer Tomans
_MILLIARD = 1_000_000_000
_MILLION = 1_000_000

# Fields reported in `missing` when not found in the transcript
_KEY_FIELDS = [
    "area",
    "rooms",
    "sale_price",
    "mortgage_amount",
    "rent_amount",
    "floor",
    "total_floors",
    "build_year",
    "property_type",
    "direction",
    "district",
]

_BOOL_FIELDS = ["parking", "elevator", "storage", "balcony"]

# Fields the LLM path may return (whitelist for normalization)
ALLOWED_DRAFT_FIELDS = _KEY_FIELDS + _BOOL_FIELDS + [
    "deal_type",
    "title",
    "neighborhood",
]


def score_draft(data: dict) -> tuple[list[str], float]:
    """
    Compute (missing, confidence) for an extracted draft by value.

    Used by the LLM path (which only has final values, no detection set).
    A field counts as found when present and not None/""/False.
    """
    required = ["area", "rooms"]
    deal = data.get("deal_type")
    if deal == "sale":
        required.append("sale_price")
    elif deal in ("rent", "mortgage_rent"):
        required += ["rent_amount", "mortgage_amount"]
    missing = [f for f in required if data.get(f) is None]

    scored = _KEY_FIELDS + _BOOL_FIELDS
    found = sum(1 for f in scored if data.get(f) not in (None, "", False))
    confidence = round(found / len(scored), 2) if scored else 0.0
    return missing, confidence

# ─── Regexes (applied to normalised text) ─────────────────────────────────────

# Persian/Arabic *letters only* — punctuation (، ؛ ؟) and tatweel are excluded
# so tokens never glue to the following word.
_FA = r"[\u0621-\u063A\u0641-\u064A\u067E\u0686\u0698\u06A9\u06AF\u06CC]"


def _num_pattern(capture: bool) -> str:
    group = "(" if capture else "(?:"
    return group + r"\d+|" + _FA + r"+(?:\sو\s" + _FA + r"+)*)"


_NUM = _num_pattern(capture=True)
_NUM_NC = _num_pattern(capture=False)
_NUM_SRC = r"\d+|" + _FA + r"+(?:\sو\s" + _FA + r"+)*"

_RE_AREA = re.compile(_NUM + r"\s*متر")
_RE_ROOMS = re.compile(_NUM + r"\s*(?:اتاق|خواب)")
_RE_FLOOR_TOTAL = re.compile(
    r"طبقه\s*(" + _NUM_NC + r")\s*از\s*(" + _NUM_NC + r")\s*طبقه"
)
_RE_FLOOR = re.compile(r"طبقه\s*" + _NUM)
_RE_FLOOR_BEFORE = re.compile(_NUM + r"\s*طبقه")
_RE_BUILD_YEAR = re.compile(r"ساخت\s*(\d{2,4})")
# Compound prices: «یک میلیارد و دویست میلیون» → one match, summed
# Groups: 1=num1, 2=unit1, 3=num2 (optional), 4=unit2 (optional)
_RE_PRICE = re.compile(
    "(" + _NUM_SRC + r")\s*(میلیارد|میلیون)"
    r"(?:\s*و\s*(" + _NUM_SRC + r")\s*(میلیارد|میلیون))?"
    r"(?:\s*تومان?)?"
)
_RE_DISTRICT = re.compile(
    r"(?:محله‌?ی?\s*)(" + _FA + r"{2,}(?:\s" + _FA + r"{2,})?)"
)


def _to_int(raw: str, table: dict[str, int] | None = None) -> int | None:
    """Parse a Persian digit-run or word-number into an int."""
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)
    # Default to the full price-word table (superset: units, teens, tens, hundreds)
    return _word_to_num(raw, table or _PRICE_WORDS)


def _has_negation(text: str, position: int, keyword: str) -> bool:
    """True when the keyword occurrence is negated nearby (بدون X / X ندارد)."""
    window = text[max(0, position - 15) : position + len(keyword) + 15]
    return ("بدون" in window) or ("ندارد" in window) or ("نفی" in window)


def _parse_price(
    text: str, data: dict, found: set[str]
) -> None:
    """
    Extract prices from `X میلیارد/میلیون تومان` occurrences.

    Compound prices («یک میلیارد و دویست میلیون») are summed in one match.
    Context decides the slot: after «رهن» → mortgage_amount, after
    «اجاره» → rent_amount, otherwise sale_price.
    """
    for match in _RE_PRICE.finditer(text):
        raw_num, unit = match.group(1), match.group(2)
        value = _to_int(raw_num, _PRICE_WORDS)
        if value is None:
            continue
        amount = value * (_MILLIARD if unit == "میلیارد" else _MILLION)

        raw_num2, unit2 = match.group(3), match.group(4)
        if raw_num2 and unit2:
            value2 = _to_int(raw_num2, _PRICE_WORDS)
            if value2 is not None:
                amount += value2 * (_MILLIARD if unit2 == "میلیارد" else _MILLION)

        before = text[max(0, match.start() - 12) : match.start()]
        if "رهن" in before:
            key = "mortgage_amount"
        elif "اجاره" in before:
            key = "rent_amount"
        else:
            key = "sale_price"
        data[key] = amount
        found.add(key)


def parse_listing_transcript(text: str) -> dict:
    """
    Parse a Persian property description into structured listing fields.

    Returns:
        {
            "data":     {field: value, ...}   # only found fields
            "missing":  [field, ...]          # key fields not found
            "confidence": float               # found / total key fields
        }
    """
    text = normalize_fa(text or "")
    # Whisper writes compound words like «دوخوابه» / «هشتادمتری» — split them
    # so the regexes see "دو خوابه" / "هشتاد متر".
    for word in _WORD_NUMS:
        text = text.replace(word + "خواب", word + " خواب")
        text = text.replace(word + "متر", word + " متر")
        text = text.replace("طبقه" + word, "طبقه " + word)
    data: dict = {}
    found: set[str] = set()

    # --- Area ------------------------------------------------------------
    if (m := _RE_AREA.search(text)) and (value := _to_int(m.group(1))) is not None:
        data["area"] = value
        found.add("area")

    # --- Rooms -------------------------------------------------------------
    if (m := _RE_ROOMS.search(text)) and (value := _to_int(m.group(1))) is not None:
        data["rooms"] = value
        found.add("rooms")

    # --- Floors: "طبقه سوم از ۵ طبقه" ---------------------------------------
    if (m := _RE_FLOOR_TOTAL.search(text)) and (
        floor := _to_int(m.group(1))
    ) is not None and (total := _to_int(m.group(2))) is not None:
        data["floor"] = floor
        data["total_floors"] = total
        found.update({"floor", "total_floors"})

    if "floor" not in found:
        if (m := _RE_FLOOR.search(text)) and (value := _to_int(m.group(1))) is not None:
            data["floor"] = value
            found.add("floor")
        elif (m := re.search(r"همکف", text)) :
            data["floor"] = 0
            found.add("floor")

    if "total_floors" not in found:
        if (m := _RE_FLOOR_BEFORE.search(text)) and (
            value := _to_int(m.group(1))
        ) is not None:
            data["total_floors"] = value
            found.add("total_floors")

    # --- Build year (شمسی → میلادی) ----------------------------------------
    if m := _RE_BUILD_YEAR.search(text):
        raw = m.group(1)
        year = int(raw)
        if len(raw) <= 2:
            year += 1300  # «ساخت ۹۰» → 1390 شمسی
        if 1300 <= year <= 1499:  # Jalali range
            year += 621  # → Gregorian
        if 1900 <= year <= 2121:
            data["build_year"] = year
            found.add("build_year")

    # --- Prices --------------------------------------------------------------
    _parse_price(text, data, found)

    # Deal type: presence of rent/mortgage keywords
    if "mortgage_amount" in found and "rent_amount" in found:
        data["deal_type"] = "mortgage_rent"
    elif "rent_amount" in found or "mortgage_amount" in found:
        data["deal_type"] = "rent"
    elif "رهن" in text or "اجاره" in text:
        data["deal_type"] = "rent"
    else:
        data["deal_type"] = "sale"
    found.add("deal_type")

    # --- Property type -------------------------------------------------------
    for keyword, value in _PROPERTY_TYPE_KEYWORDS:
        if keyword in text:
            data["property_type"] = value
            found.add("property_type")
            break

    # --- Direction -------------------------------------------------------------
    for keyword, value in _DIRECTION_KEYWORDS:
        if keyword in text:
            data["direction"] = value
            found.add("direction")
            break

    # --- Amenities (respect negation) -----------------------------------------
    for field, keyword in _AMENITY_KEYWORDS.items():
        if m := re.search(keyword, text):
            data[field] = not _has_negation(text, m.start(), keyword)
            found.add(field)

    # --- District (plain text; service resolves the Neighborhood FK) ----------
    if m := _RE_DISTRICT.search(text):
        # Strip Persian/Latin punctuation — the char class swallows «،»
        district = re.split(r"[،,؛]", m.group(1))[0].strip()
        if district:
            data["district"] = district
            found.add("district")

    # --- Missing & confidence ---------------------------------------------------
    # Required fields depend on the deal type: a sale needs a sale price,
    # a rent/mortgage needs rent and mortgage amounts.
    required = ["area", "rooms"]
    deal = data.get("deal_type")
    if deal == "sale":
        required.append("sale_price")
    elif deal in ("rent", "mortgage_rent"):
        required += ["rent_amount", "mortgage_amount"]
    missing = [f for f in required if f not in found]

    scored = _KEY_FIELDS + _BOOL_FIELDS
    confidence = round(len(found & set(scored)) / len(scored), 2) if scored else 0.0

    return {"data": data, "missing": missing, "confidence": confidence}
