"""
Listings URL configuration.
"""

from django.urls import path

from apps.listings import views

app_name = "listings"

urlpatterns = [
    path("", views.ListingListView.as_view(), name="list"),
    path("add/", views.ListingCreateView.as_view(), name="create"),
    path("<int:pk>/", views.ListingDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.ListingUpdateView.as_view(), name="update"),
    path("<int:pk>/status/", views.listing_status_update, name="status_update"),
]
