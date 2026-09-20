"""URL patterns for accounts app."""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("otp/", views.otp_verify_view, name="otp-verify"),
    path("logout/", views.logout_view, name="logout"),
]
