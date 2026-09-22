"""
Listings URL configuration.
"""

from django.urls import path

from apps.listings import media_views, views

app_name = "listings"

urlpatterns = [
    path("", views.ListingListView.as_view(), name="list"),
    path("add/", views.ListingCreateView.as_view(), name="create"),
    path("<int:pk>/", views.ListingDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.ListingUpdateView.as_view(), name="update"),
    path("<int:pk>/status/", views.listing_status_update, name="status_update"),
    # Phase 1C — Media
    path("<int:pk>/media/upload/", media_views.media_upload_view, name="media_upload"),
    path(
        "<int:pk>/media/<int:media_pk>/delete/",
        media_views.media_delete_view,
        name="media_delete",
    ),
    path("<int:pk>/media/reorder/", media_views.media_reorder_view, name="media_reorder"),
    path(
        "<int:pk>/media/<int:media_pk>/cover/",
        media_views.media_set_cover_view,
        name="media_set_cover",
    ),
    # Signed URL for private documents (no auth required — token IS auth)
    path("media/private/<str:token>/", media_views.media_serve_private, name="media_serve_private"),
]
