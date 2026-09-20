"""
OTP authentication API views (DRF).

These are JSON endpoints consumed by the HTMX/JS frontend and mobile clients.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.otp import send_otp, verify_otp

User = get_user_model()


class PhoneSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(min_length=4, max_length=8)


class OTPSendView(APIView):
    """
    POST /api/auth/otp/send/
    Body: {"phone": "09XXXXXXXXX"}
    Triggers OTP generation and SMS dispatch (Celery task).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        send_otp(phone)
        return Response({"detail": "کد تأیید ارسال شد."}, status=status.HTTP_200_OK)


class OTPVerifyView(APIView):
    """
    POST /api/auth/otp/verify/
    Body: {"phone": "09XXXXXXXXX", "code": "123456"}
    Returns JWT tokens on success.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]

        if not verify_otp(phone, code):
            return Response(
                {"detail": "کد نادرست یا منقضی شده است."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={"is_active": True},
        )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "created": created,
            },
            status=status.HTTP_200_OK,
        )
