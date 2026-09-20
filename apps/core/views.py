"""Core app views: health check and homepage."""

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.core.health import get_health_status


@never_cache
@require_GET
def health_view(request):
    """
    GET /health/
    Returns JSON: {"status": "ok", "db": "ok", "redis": "ok", "celery": "ok"}
    HTTP 200 if all healthy, 503 if any check fails.
    """
    payload, status_code = get_health_status()
    return JsonResponse(payload, status=status_code)


def homepage_view(request):
    """GET / — Simple RTL Farsi homepage."""
    return render(request, "home.html")
