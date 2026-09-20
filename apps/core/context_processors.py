"""Template context processors for global UI variables."""

from django.conf import settings


def ui_context(request):
    """Inject global UI variables into every template context."""
    return {
        "LANGUAGE_CODE": settings.LANGUAGE_CODE,
        "RTL": True,
    }
