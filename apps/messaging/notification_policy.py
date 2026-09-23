"""
Notification Policy service — Phase 4B

Implements the pure-function policy that decides whether an SMS should be sent
for a given (match, agency) pair, and the send pipeline:

  MatchRecord → should_send_sms(policy, match, now) → enqueue_sms / notify_agent

Public API:
- should_send_sms(policy, match, now) → bool   (pure, testable)
- process_match_notification(match)             (side-effecting, calls enqueue_sms)
- send_renewal_sms(request)                     (sends renewal reminder)
- handle_unsubscribe(token)                     (revokes consent)
- handle_renewal(token, action)                 (renew or stop request)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from django.utils import timezone

if TYPE_CHECKING:
    from apps.matching.models import Match
    from apps.messaging.models import AgencySMSPolicy

logger = logging.getLogger(__name__)

# Score tiers used by the policy
SCORE_EXACT = 80   # ≥ 80  → "exact"
SCORE_STRONG = 50  # ≥ 50  → "strong"


# ─── Pure policy function ─────────────────────────────────────────────────────


def should_send_sms(
    policy: AgencySMSPolicy,
    score: int,
    contact_daily_count: int,
    has_consent: bool,
    already_sent: bool,
    current_hour: int,
) -> tuple[bool, str]:
    """
    Pure function: decides whether to auto-send an SMS.

    Returns (send: bool, reason: str).

    Rules (in order):
    1. Master switch off  → no
    2. No consent          → no
    3. Already sent for this (listing, request) pair → no (dedup)
    4. Score < 50          → no  (below minimum for any auto-send)
    5. Quiet hours         → no
    6. Daily cap reached   → no
    7. Score < threshold and strong-send disabled → no
    8. → yes
    """
    if not policy.is_active:
        return False, "policy_inactive"
    if not has_consent:
        return False, "no_consent"
    if already_sent:
        return False, "already_sent"
    if score < SCORE_STRONG:
        return False, "score_too_low"

    # Quiet hours check
    qs = policy.quiet_start
    qe = policy.quiet_end
    in_quiet = (
        (qs < qe and qs <= current_hour < qe)          # e.g. 02:00–08:00
        or (qs > qe and (current_hour >= qs or current_hour < qe))  # e.g. 22:00–08:00
        or (qs == qe)  # never quiet (shouldn't happen but safe)
    )
    if in_quiet:
        return False, "quiet_hours"

    if contact_daily_count >= policy.daily_cap:
        return False, "daily_cap"

    # Score tier check
    if score >= policy.score_threshold:
        if policy.auto_send_exact:
            return True, "exact_match"
    elif score >= SCORE_STRONG:
        if policy.auto_send_strong:
            return True, "strong_match"

    return False, "not_auto_send_tier"


# ─── Process match notification ───────────────────────────────────────────────


def process_match_notification(match: Match) -> None:
    """
    Evaluate the notification policy for a match and either:
    - enqueue an SMS (for exact/strong matches with consent)
    - create an in-app CRM Notification for the agent (for near matches)

    This is called from the matching Celery task after matches are persisted.
    """
    from django.utils import timezone

    from apps.crm.services import notify
    from apps.messaging.models import (
        AgencySMSPolicy,
        MatchSMSSent,
        SMSMessage,
        SMSMessageState,
    )
    from apps.messaging.services import enqueue_sms

    agency = match.agency
    request = match.request
    listing = match.listing
    contact = request.contact

    # ── Near match: notify agent only ────────────────────────────────────────
    if match.score < SCORE_STRONG:
        notify(
            agency=agency,
            user=request.assigned_to or agency.members.filter(role="owner").first().user
            if agency.members.filter(role="owner").exists()
            else None,
            kind="match",
            body=f"تطبیق نزدیک: فایل {listing.code or listing.pk} برای {contact}",
            listing=listing,
            request=request,
        )
        return

    # ── Check dedup ───────────────────────────────────────────────────────────
    already_sent = MatchSMSSent.objects.filter(listing=listing, request=request).exists()

    # ── Get/create policy ─────────────────────────────────────────────────────
    policy = AgencySMSPolicy.objects.filter(agency=agency, is_active=True).first()
    if policy is None:
        # No policy → notify agent in-app only
        _notify_agent(agency, listing, request, contact, match.score)
        return

    # ── Check consent ─────────────────────────────────────────────────────────
    # is_active is a property, not a DB field — filter by revoked_at__isnull
    has_consent = contact.consent_records.filter(
        revoked_at__isnull=True
    ).exists() if contact else False

    # ── Count today's SMS to this contact ────────────────────────────────────
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    daily_count = SMSMessage.objects.filter(
        agency=agency,
        contact=contact,
        created_at__gte=today_start,
        state__in=[SMSMessageState.QUEUED, SMSMessageState.SENT, SMSMessageState.DELIVERED],
    ).count() if contact else 0

    now_local = timezone.localtime(timezone.now())
    current_hour = now_local.hour

    send, reason = should_send_sms(
        policy=policy,
        score=match.score,
        contact_daily_count=daily_count,
        has_consent=has_consent,
        already_sent=already_sent,
        current_hour=current_hour,
    )

    if send:
        phone = _get_contact_phone(contact)
        if not phone:
            logger.warning(
                "process_match_notification: no phone for contact %s — skipping SMS", contact
            )
            _notify_agent(agency, listing, request, contact, match.score)
            return

        body = _build_sms_body(policy, listing, contact, agency)
        sms = enqueue_sms(
            agency=agency,
            to=phone,
            body=body,
            contact=contact,
            template=policy.match_template,
        )
        MatchSMSSent.objects.get_or_create(
            listing=listing,
            request=request,
            defaults={"agency": agency, "sms": sms},
        )
        logger.info(
            "process_match_notification: SMS enqueued for match listing=%s req=%s",
            listing.pk,
            request.pk,
        )
    else:
        logger.info(
            "process_match_notification: SMS suppressed reason=%s listing=%s req=%s",
            reason,
            listing.pk,
            request.pk,
        )
        # Always notify agent
        _notify_agent(agency, listing, request, contact, match.score)


def _notify_agent(agency, listing, request, contact, score):
    """Create an in-app notification for the assigned agent."""
    from apps.crm.services import notify

    assigned = request.assigned_to
    if assigned is None:
        return
    notify(
        agency=agency,
        user=assigned,
        kind="match",
        body=(
            f"تطبیق جدید (امتیاز {score}): فایل {listing.code or listing.pk}"
            f" برای {contact}"
        ),
        listing=listing,
        request=request,
    )


def _get_contact_phone(contact) -> str | None:
    """Return the primary mobile phone of a contact, or None."""
    if contact is None:
        return None
    phone_obj = contact.phones.filter(label="mobile").first() or contact.phones.first()
    if phone_obj is None:
        return None
    return phone_obj.phone_normalized or None


def _build_sms_body(policy, listing, contact, agency) -> str:
    """Build the SMS text using the policy template or a default."""
    code = str(listing.code) if getattr(listing, "code", None) else str(listing.pk)
    prop_type = (
        listing.get_property_type_display()
        if hasattr(listing, "get_property_type_display")
        else ""
    )
    ctx = {
        "نام": str(contact) if contact else "",
        "نام_آژانس": agency.name,
        "تلفن_آژانس": agency.phone or "",
        "کد_فایل": code,
        "نوع_ملک": prop_type,
        "محله": str(listing.neighborhood) if listing.neighborhood else "",
    }
    if policy.match_template:
        return policy.match_template.render(ctx)
    # Default fallback text
    return (
        f"مراجعه‌کننده گرامی {ctx['نام']}،\n"
        f"یک فایل ملکی مناسب برای شما ثبت شد.\n"
        f"لطفاً با آژانس {ctx['نام_آژانس']} تماس بگیرید.\n"
        f"تلفن: {ctx['تلفن_آژانس']}"
    )


# ─── Unsubscribe ─────────────────────────────────────────────────────────────


def handle_unsubscribe(token: str) -> bool:
    """
    Verify the unsubscribe token and revoke the contact's SMS consent.

    Returns True if consent was successfully revoked, False if token is invalid.
    """
    from apps.messaging.models import verify_unsubscribe_token

    contact_id = verify_unsubscribe_token(token)
    if contact_id is None:
        return False

    from apps.crm.models import ConsentRecord

    now = timezone.now()
    # is_active is a property, not a DB field — filter by revoked_at__isnull
    updated = ConsentRecord.objects.filter(
        contact_id=contact_id,
        revoked_at__isnull=True,
    ).update(revoked_at=now)
    logger.info("Unsubscribe: contact_id=%d — %d consent(s) revoked", contact_id, updated)
    return True


# ─── Renewal ─────────────────────────────────────────────────────────────────


def handle_renewal(token: str, action: Literal["renew", "stop"]) -> bool:
    """
    Handle a renewal/stop action from the renewal SMS link.

    Returns True if action was applied, False if token invalid.
    """
    from apps.crm.models import Request, RequestStatus
    from apps.messaging.models import verify_renewal_token

    request_id = verify_renewal_token(token)
    if request_id is None:
        return False

    try:
        req = Request.objects.get(pk=request_id)
    except Request.DoesNotExist:
        return False

    if action == "renew":
        from datetime import timedelta

        req.expires_at = timezone.now() + timedelta(days=90)
        req.save(update_fields=["expires_at"])
        logger.info("Renewal: request %d renewed until %s", request_id, req.expires_at)
    else:  # stop
        req.status = RequestStatus.CLOSED
        req.save(update_fields=["status"])
        logger.info("Renewal: request %d stopped by token", request_id)

    return True


def send_renewal_sms(request) -> None:
    """Send a renewal-reminder SMS to the contact before request expiry."""
    from apps.messaging.models import make_renewal_token
    from apps.messaging.services import enqueue_sms

    contact = request.contact
    phone = _get_contact_phone(contact)
    if not phone:
        return

    token_renew = make_renewal_token(request.pk)
    token_stop = make_renewal_token(request.pk)  # same token — action determined by URL

    body = (
        f"مراجعه‌کننده گرامی،\n"
        f"درخواست شما در حال انقضاست.\n"
        f"برای تمدید: /messaging/renew/{token_renew}/renew/\n"
        f"برای توقف: /messaging/renew/{token_stop}/stop/"
    )
    enqueue_sms(agency=request.agency, to=phone, body=body, contact=contact)
