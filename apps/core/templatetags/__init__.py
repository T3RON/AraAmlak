"""
Core app template tags.
"""

from django import template

from apps.core.currency import format_number_fa, format_toman, to_persian_digits

register = template.Library()


@register.filter(name="toman")
def toman_filter(value):
    """Format integer as Persian Toman string. Usage: {{ price|toman }}"""
    try:
        return format_toman(int(value))
    except (TypeError, ValueError):
        return value


@register.filter(name="fa_number")
def fa_number_filter(value):
    """Convert digits to Persian. Usage: {{ count|fa_number }}"""
    return to_persian_digits(str(value))


@register.filter(name="fa_format")
def fa_format_filter(value):
    """Format number with Persian digits and thousand separator."""
    try:
        return format_number_fa(int(value))
    except (TypeError, ValueError):
        return value
