"""Minimal URLconf for health tests ظ¤ avoids GIS/accounts import chain."""

from django.urls import path

from apps.core.views import health_view, homepage_view

urlpatterns = [
    path("health/", health_view),
    path("", homepage_view),
]
