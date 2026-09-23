"""
Messaging app views — Phase 4B

Views:
- PublicSubscribeView     : public form for agency subscription + OTP verification
- UnsubscribeView         : revokes SMS consent via signed token
- RenewalView             : renews or stops a CRM Request via signed token
- AgencySMSConfigView     : internal — agency owner configures SMS provider (stub)
"""

from __future__ import annotations

import logging

from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.agencies.models import Agency
from apps.core.text import normalize_phone_ir

logger = logging.getLogger(__name__)

# Rate limits
_OTP_RATE_PREFIX = "pub_sub_otp:"
_OTP_IP_PREFIX = "pub_sub_otp_ip:"
_MAX_OTP_PER_NUMBER = 5   # per hour
_MAX_OTP_PER_IP = 10      # per hour
_OTP_RATE_TTL = 3600      # 1 hour


def _check_rate_limit(cache_key: str, limit: int, ttl: int) -> bool:
    """Return True if rate limit is NOT exceeded (request is allowed)."""
    count = cache.get(cache_key, 0)
    if count >= limit:
        return False
    cache.set(cache_key, count + 1, timeout=ttl)
    return True


class PublicSubscribeView(View):
    """
    Two-step public subscription form for an agency.

    Step 1 (GET / POST phone): collect name + phone + requirements, send OTP
    Step 2 (POST verify): verify OTP, create Contact + Request + ConsentRecord

    URL: /messaging/subscribe/<agency_slug>/
    """

    template_step1 = "messaging/public_subscribe.html"
    template_step2 = "messaging/public_subscribe_verify.html"

    def get(self, request, agency_slug: str):
        agency = get_object_or_404(Agency, slug=agency_slug, is_active=True)
        from apps.listings.models import DealType, PropertyType

        return render(
            request,
            self.template_step1,
            {
                "agency": agency,
                "deal_types": DealType.choices,
                "property_types": PropertyType.choices,
            },
        )

    def post(self, request, agency_slug: str):
        agency = get_object_or_404(Agency, slug=agency_slug, is_active=True)
        step = request.POST.get("step", "1")

        if step == "1":
            return self._handle_step1(request, agency)
        if step == "2":
            return self._handle_step2(request, agency)
        return HttpResponseBadRequest("invalid step")

    # ── Step 1: collect data, send OTP ───────────────────────────────────────

    def _handle_step1(self, request, agency):
        phone_raw = request.POST.get("phone", "").strip()
        name = request.POST.get("name", "").strip()
        consent = request.POST.get("consent", "")

        if not phone_raw or not name:
            messages.error(request, _("نام و شماره موبایل الزامی است."))
            return redirect("messaging:public_subscribe", agency_slug=agency.slug)

        if not consent:
            messages.error(request, _("برای ادامه باید رضایت دریافت پیامک را تأیید کنید."))
            return redirect("messaging:public_subscribe", agency_slug=agency.slug)

        phone = normalize_phone_ir(phone_raw)
        if not phone:
            messages.error(request, _("شماره موبایل معتبر نیست."))
            return redirect("messaging:public_subscribe", agency_slug=agency.slug)

        # Honeypot field check
        if request.POST.get("website", ""):
            return redirect("messaging:public_subscribe", agency_slug=agency.slug)

        # Rate limits
        ip = request.META.get("REMOTE_ADDR", "unknown")
        if not _check_rate_limit(f"{_OTP_RATE_PREFIX}{phone}", _MAX_OTP_PER_NUMBER, _OTP_RATE_TTL):
            messages.error(request, _("درخواست‌های زیادی فرستادید. کمی صبر کنید."))
            return redirect("messaging:public_subscribe", agency_slug=agency.slug)
        if not _check_rate_limit(f"{_OTP_IP_PREFIX}{ip}", _MAX_OTP_PER_IP, _OTP_RATE_TTL):
            messages.error(request, _("درخواست‌های زیادی فرستادید. کمی صبر کنید."))
            return redirect("messaging:public_subscribe", agency_slug=agency.slug)

        # Store form data in session (not sensitive beyond phone)
        request.session[f"pub_sub_{agency.slug}"] = {
            "phone": phone,
            "name": name,
            "deal_type": request.POST.get("deal_type", ""),
            "property_types": request.POST.getlist("property_types"),
            "city": request.POST.get("city", ""),
            "min_budget": request.POST.get("min_budget", ""),
            "max_budget": request.POST.get("max_budget", ""),
            "min_area": request.POST.get("min_area", ""),
            "max_area": request.POST.get("max_area", ""),
            "min_rooms": request.POST.get("min_rooms", ""),
            "max_rooms": request.POST.get("max_rooms", ""),
            "notes": request.POST.get("notes", ""),
        }

        # Send OTP
        from apps.accounts.otp import send_otp
        send_otp(phone)

        return render(
            request,
            self.template_step2,
            {"agency": agency, "phone_masked": f"****{phone[-4:]}"},
        )

    # ── Step 2: verify OTP, create records ───────────────────────────────────

    def _handle_step2(self, request, agency):
        session_key = f"pub_sub_{agency.slug}"
        session_data = request.session.get(session_key)

        if not session_data:
            messages.error(request, _("جلسه منقضی شده. لطفاً دوباره فرم را تکمیل کنید."))
            return redirect("messaging:public_subscribe", agency_slug=agency.slug)

        code = request.POST.get("otp_code", "").strip()
        phone = session_data["phone"]

        from apps.accounts.otp import verify_otp

        if not verify_otp(phone, code):
            messages.error(request, _("کد تأیید اشتباه یا منقضی شده است."))
            return render(
                request,
                self.template_step2,
                {"agency": agency, "phone_masked": f"****{phone[-4:]}"},
            )

        # OTP verified — create Contact, Request, ConsentRecord
        self._create_subscription(request, agency, session_data, phone)
        del request.session[session_key]

        return render(
            request,
            "messaging/public_subscribe_done.html",
            {"agency": agency},
        )

    def _create_subscription(self, request, agency, data: dict, phone: str):
        """Create Contact + ContactPhone + ConsentRecord + Request from form data."""
        from django.db import transaction

        from apps.crm.models import (
            ConsentRecord,
            ConsentSource,
            Contact,
            ContactPhone,
            PhoneLabel,
            Request,
            RequestSource,
        )

        with transaction.atomic():
            # Get or create contact by phone
            phone_obj = ContactPhone.objects.filter(
                phone_normalized=phone, contact__agency=agency
            ).select_related("contact").first()

            if phone_obj:
                contact = phone_obj.contact
            else:
                contact = Contact.objects.create(
                    agency=agency,
                    full_name=data["name"],
                )
                ContactPhone.objects.create(
                    contact=contact,
                    phone=phone,            # encrypted field
                    phone_normalized=phone,
                    label=PhoneLabel.MOBILE,
                    is_primary=True,
                )

            # Record consent
            ConsentRecord.objects.create(
                contact=contact,
                agency=agency,
                source=ConsentSource.PUBLIC_FORM,
                text_version="v1",
            )

            # Create Request
            req_data: dict = {
                "agency": agency,
                "contact": contact,
                "source": RequestSource.PUBLIC_FORM,
                "notes": data.get("notes", ""),
            }
            if data.get("deal_type"):
                req_data["deal_type"] = data["deal_type"]
            for field in ("city", "min_budget", "max_budget", "min_area", "max_area",
                          "min_rooms", "max_rooms"):
                val = data.get(field, "")
                if val:
                    try:
                        req_data[field] = int(val) if field not in ("city",) else val
                    except (ValueError, TypeError):
                        pass
            if data.get("property_types"):
                req_data["property_types"] = data["property_types"]

            Request.objects.create(**req_data)

        logger.info("PublicSubscribe: contact=%d agency=%s", contact.pk, agency.slug)


# ─── Unsubscribe ─────────────────────────────────────────────────────────────


class UnsubscribeView(View):
    """
    Revoke SMS consent via a signed token embedded in every outgoing SMS.

    URL: /messaging/unsubscribe/<token>/
    """

    def get(self, request, token: str):
        from apps.messaging.notification_policy import handle_unsubscribe

        success = handle_unsubscribe(token)
        return render(
            request,
            "messaging/unsubscribe.html",
            {"success": success},
        )


# ─── Renewal ─────────────────────────────────────────────────────────────────


class RenewalView(View):
    """
    Renew or stop a CRM Request via a signed token.

    URL: /messaging/renew/<token>/<action>/   action = "renew" | "stop"
    """

    def get(self, request, token: str, action: str):
        from apps.messaging.notification_policy import handle_renewal

        if action not in ("renew", "stop"):
            return HttpResponseBadRequest("invalid action")

        success = handle_renewal(token, action)  # type: ignore[arg-type]
        return render(
            request,
            "messaging/renewal.html",
            {"success": success, "action": action},
        )
