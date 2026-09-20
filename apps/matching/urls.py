"""URL patterns for the matching app."""

from django.urls import path

from apps.matching.views import RequestMatchListView

app_name = "matching"

urlpatterns = [
    path(
        "requests/<int:pk>/matches/",
        RequestMatchListView.as_view(),
        name="request_matches",
    ),
]
