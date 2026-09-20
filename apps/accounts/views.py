"""Template-based auth views (session login via OTP)."""

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.shortcuts import redirect, render

from apps.accounts.otp import send_otp, verify_otp

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
            # In DEBUG mode, show the OTP code on the verify page (no real SMS)
            if _s.DEBUG:
                _debug_code = _c.get(f"otp:{phone}")
                request.session["_debug_otp"] = _debug_code
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
            messages.success(request, f"خوش آمدید، {user.get_short_name()}!")
            return redirect("dashboard:home")
        messages.error(request, "کد نادرست یا منقضی شده است.")
    return render(request, "accounts/otp_verify.html", {"phone": phone})


def logout_view(request):
    """Log out and redirect to login."""
    logout(request)
    return redirect("accounts:login")
