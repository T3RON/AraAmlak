"""
Currency and number formatting utilities for Ara Amlak.

All amounts stored in Tomans (BigInteger).
Display format: «۲ میلیارد و ۷۰۰ میلیون تومان»
"""

from __future__ import annotations

_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_ARABIC_TO_PERSIAN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "۰۱۲۳۴۵۶۷۸۹")

BILLION = 1_000_000_000
MILLION = 1_000_000
THOUSAND = 1_000


def to_persian_digits(value: str | int) -> str:
    """Convert ASCII/Arabic digits to Persian digits."""
    return str(value).translate(_PERSIAN_DIGITS).translate(_ARABIC_TO_PERSIAN)


def format_toman(amount: int) -> str:
    """
    Format a Toman integer amount as a human-readable Persian string.

    Examples:
        format_toman(2_700_000_000)  → "۲ میلیارد و ۷۰۰ میلیون تومان"
        format_toman(1_500_000)      → "۱ میلیون و ۵۰۰ هزار تومان"
        format_toman(250_000)        → "۲۵۰ هزار تومان"
        format_toman(5_000)          → "۵٬۰۰۰ تومان"
        format_toman(0)              → "رایگان"
    """
    if not isinstance(amount, int):
        amount = int(amount)

    if amount == 0:
        return "رایگان"
    if amount < 0:
        return f"({format_toman(-amount)}-)"

    parts: list[str] = []
    remainder = amount

    billions, remainder = divmod(remainder, BILLION)
    if billions:
        parts.append(f"{to_persian_digits(billions)} میلیارد")

    millions, remainder = divmod(remainder, MILLION)
    if millions:
        parts.append(f"{to_persian_digits(millions)} میلیون")

    thousands, remainder = divmod(remainder, THOUSAND)
    if thousands:
        parts.append(f"{to_persian_digits(thousands)} هزار")

    if remainder:
        parts.append(to_persian_digits(remainder))

    # If total is less than 1000, show with thousand-separator
    if amount < THOUSAND:
        formatted = f"{amount:,}".replace(",", "٬")
        return f"{to_persian_digits(formatted)} تومان"

    return " و ".join(parts) + " تومان"


def format_number_fa(value: int | float, decimal_places: int = 0) -> str:
    """Format a number with Persian digits and thousand separator."""
    if decimal_places:
        formatted = f"{value:,.{decimal_places}f}"
    else:
        formatted = f"{int(value):,}"
    formatted = formatted.replace(",", "٬").replace(".", "٫")
    return to_persian_digits(formatted)
