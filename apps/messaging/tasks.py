"""
Celery tasks for the messaging app.

Tasks:
- send_sms_task: deliver a queued SMSMessage with retry and exponential backoff.
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)

_MAX_RETRIES = 5
_BACKOFF_BASE = 60  # seconds — doubles each retry: 60, 120, 240, 480, 960


@shared_task(
    bind=True,
    max_retries=_MAX_RETRIES,
    acks_late=True,
    name="apps.messaging.tasks.send_sms_task",
)
def send_sms_task(self, sms_id: int, to: str) -> None:
    """
    Send a queued SMSMessage to the provider.

    Retries up to _MAX_RETRIES times with exponential backoff on any error.
    The `to` phone number is passed as a task argument so it is never stored
    in the SMSMessage log (only the masked form is).
    """
    from apps.messaging.services import send_sms_message

    try:
        send_sms_message(sms_id, to)
    except Exception as exc:
        countdown = _BACKOFF_BASE * (2 ** self.request.retries)
        logger.warning(
            "send_sms_task: SMS #%d attempt %d failed — retry in %ds: %s",
            sms_id,
            self.request.retries + 1,
            countdown,
            exc,
        )
        raise self.retry(exc=exc, countdown=countdown) from exc


@shared_task(
    name="apps.messaging.tasks.send_renewal_reminders",
    acks_late=True,
)
def send_renewal_reminders_task() -> None:
    """
    Beat task — runs daily at 09:00 Tehran time.

    Finds CRM Requests that expire within the next 3 days and sends renewal
    reminder SMS to contacts that have active consent.
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.crm.models import Request, RequestStatus
    from apps.messaging.notification_policy import send_renewal_sms

    threshold = timezone.now().date() + timedelta(days=3)
    active_statuses = [RequestStatus.NEW, RequestStatus.IN_PROGRESS, RequestStatus.MATCHED]
    expiring = Request.objects.filter(
        status__in=active_statuses,
        expires_at__lte=threshold,
        expires_at__gt=timezone.now().date(),
        contact__consent_records__revoked_at__isnull=True,
    ).select_related("contact", "agency").distinct()

    count = 0
    for req in expiring:
        try:
            send_renewal_sms(req)
            count += 1
        except Exception as exc:
            logger.error("send_renewal_reminders_task: request=%d error=%s", req.pk, exc)

    logger.info("send_renewal_reminders_task: sent %d renewal SMS", count)
