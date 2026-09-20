"""API URL configuration."""

from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.api_views import OTPSendView, OTPVerifyView

urlpatterns = [
    # Auth
    path("auth/otp/send/", OTPSendView.as_view(), name="api-otp-send"),
    path("auth/otp/verify/", OTPVerifyView.as_view(), name="api-otp-verify"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="api-token-refresh"),
    # Schema
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
