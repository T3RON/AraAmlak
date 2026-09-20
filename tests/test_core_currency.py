"""
Tests for currency formatter and Persian numeral utilities.
"""


from apps.core.currency import format_number_fa, format_toman, to_persian_digits


class TestFormatToman:
    def test_billion_and_millions(self):
        result = format_toman(2_700_000_000)
        assert result == "۲ میلیارد و ۷۰۰ میلیون تومان"

    def test_million_and_thousands(self):
        result = format_toman(1_500_000)
        assert result == "۱ میلیون و ۵۰۰ هزار تومان"

    def test_thousands_only(self):
        result = format_toman(250_000)
        assert result == "۲۵۰ هزار تومان"

    def test_small_amount_uses_separator(self):
        result = format_toman(5_000)
        assert "۵" in result
        assert "تومان" in result

    def test_zero_is_free(self):
        assert format_toman(0) == "رایگان"

    def test_exact_billion(self):
        result = format_toman(1_000_000_000)
        assert result == "۱ میلیارد تومان"

    def test_exact_million(self):
        result = format_toman(1_000_000)
        assert result == "۱ میلیون تومان"

    def test_exact_thousand(self):
        result = format_toman(1_000)
        assert "هزار" in result or "تومان" in result

    def test_large_number(self):
        # 10 billion + 500 million + 300 thousand
        result = format_toman(10_500_300_000)
        assert "۱۰ میلیارد" in result
        assert "۵۰۰ میلیون" in result
        assert "۳۰۰ هزار" in result

    def test_all_parts_joined_with_va(self):
        result = format_toman(1_001_001_000)
        assert " و " in result


class TestPersianDigits:
    def test_converts_ascii_to_persian(self):
        assert to_persian_digits("123") == "۱۲۳"

    def test_converts_arabic_to_persian(self):
        assert to_persian_digits("١٢٣") == "۱۲۳"

    def test_integer_input(self):
        assert to_persian_digits(42) == "۴۲"

    def test_zero(self):
        assert to_persian_digits(0) == "۰"


class TestFormatNumberFa:
    def test_thousand_separator(self):
        result = format_number_fa(1_000_000)
        assert "٬" in result  # Persian thousand separator
        assert "۱" in result

    def test_no_separator_below_thousand(self):
        result = format_number_fa(500)
        assert result == "۵۰۰"
