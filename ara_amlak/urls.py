"""URL configuration for Ara Amlak project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # API
    path("api/", include("ara_amlak.api_urls")),
    # Auth (session-based template views)
    path("auth/", include("apps.accounts.urls")),
    # App views
    path("", include("apps.dashboard.urls")),
]
