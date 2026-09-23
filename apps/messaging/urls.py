"""URL patterns for the messaging app."""

from django.urls import path

from .views import PublicSubscribeView, RenewalView, UnsubscribeView

app_name = "messaging"

urlpatterns = [
    # Public subscription form (agency-specific)
    path("subscribe/<slug:agency_slug>/", PublicSubscribeView.as_view(), name="public_subscribe"),
    # Unsubscribe via signed token
    path("unsubscribe/<str:token>/", UnsubscribeView.as_view(), name="unsubscribe"),
    # Renewal / stop via signed token
    path("renew/<str:token>/<str:action>/", RenewalView.as_view(), name="renewal"),
]
