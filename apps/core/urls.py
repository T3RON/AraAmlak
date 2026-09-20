"""URL patterns for core app."""

from django.urls import path

from .views import health_view, homepage_view

app_name = "core"

urlpatterns = [
    path("health/", health_view, name="health"),
    path("", homepage_view, name="home"),
]
