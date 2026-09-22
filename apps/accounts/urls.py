"""URL patterns for accounts app."""

from django.urls import path

from . import invite_views, views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("otp/", views.otp_verify_view, name="otp-verify"),
    path("logout/", views.logout_view, name="logout"),
    # Invitations
    path("invite/create/", invite_views.invite_create_view, name="invite-create"),
    path("invite/list/", invite_views.invite_list_view, name="invite-list"),
    path(
        "invite/<str:token>/accept/",
        invite_views.InviteAcceptView.as_view(),
        name="invite-accept",
    ),
]
