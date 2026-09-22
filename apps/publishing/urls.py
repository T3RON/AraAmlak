"""URL patterns for the publishing app."""

from django.urls import path

from apps.publishing.views import ListingPublishJobListView, PublishCreateView

app_name = "publishing"

urlpatterns = [
    path(
        "listings/<int:pk>/jobs/",
        ListingPublishJobListView.as_view(),
        name="job_list",
    ),
    path(
        "listings/<int:pk>/publish/",
        PublishCreateView.as_view(),
        name="publish",
    ),
]
