"""Template-based auth views (session login via OTP)."""

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.shortcuts import redirect, render

from apps.accounts.otp import send_otp, verify_otp
from apps.core.models import AuditAction, AuditLog

User = get_user_model()


def login_view(request):
    """Step 1: Show phone input or redirect if already logged in."""
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        if phone:
            from django.conf import settings as _s  # noqa: PLC0415
            from django.core.cache import cache as _c  # noqa: PLC0415
            send_otp(phone)
            request.session["otp_phone"] = phone
            # In DEBUG mode, store OTP in session under a non-underscore key
            if _s.DEBUG:
                request.session["debug_otp_code"] = _c.get(f"otp:{phone}")
            return redirect("accounts:otp-verify")
        messages.error(request, "شماره موبایل را وارد کنید.")
    return render(request, "accounts/login.html")


def otp_verify_view(request):
    """Step 2: Verify OTP and create session."""
    phone = request.session.get("otp_phone")
    if not phone:
        return redirect("accounts:login")
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        if verify_otp(phone, code):
            user, _ = User.objects.get_or_create(phone=phone, defaults={"is_active": True})
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            del request.session["otp_phone"]
            request.session.pop("debug_otp_code", None)
            AuditLog.log(
                actor=user,
                agency=getattr(user, "agency", None),
                action=AuditAction.LOGIN,
                request=request,
            )
            messages.success(request, f"خوش آمدید، {user.get_short_name()}!")
            return redirect("dashboard:home")
        messages.error(request, "کد نادرست یا منقضی شده است.")
    # Pass debug OTP to context (only present in DEBUG mode)
    ctx = {
        "phone": phone,
        "debug_otp": request.session.get("debug_otp_code"),
    }
    return render(request, "accounts/otp_verify.html", ctx)


def logout_view(request):
    """Log out and redirect to login."""
    if request.user.is_authenticated:
        AuditLog.log(
            actor=request.user,
            agency=getattr(request.user, "agency", None),
            action=AuditAction.LOGOUT,
            request=request,
        )
    logout(request)
    return redirect("accounts:login")
