"""URL configuration for Ara Amlak project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # API
    path("api/", include("ara_amlak.api_urls")),
    # Auth (session-based template views)
    path("auth/", include("apps.accounts.urls")),
    # Listings (فایل ملک)
    path("listings/", include("apps.listings.urls")),
    # CRM (درخواست)
    path("crm/requests/", include("apps.crm.urls")),
    # Matching (تطبیق فایل با درخواست)
    path("matching/", include("apps.matching.urls")),
    # App views (dashboard, health, home)
    path("", include("apps.core.urls")),
    path("", include("apps.dashboard.urls")),
]
