"""
SMS service layer — Phase 4A

Public API:
- enqueue_sms(agency, to, body, contact=None, template=None)
    Creates an SMSMessage in QUEUED state and fires the Celery task.

- send_sms_message(sms_id)
    Called by the Celery task; sends the message and transitions state.

- get_provider_for_agency(agency)
    Returns the active SMSProvider adapter for the agency, or ConsoleSMSProvider
    if no config exists.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from apps.agencies.models import Agency
    from apps.crm.models import Contact
    from apps.messaging.models import SMSMessage, SMSTemplate

logger = logging.getLogger(__name__)


# ─── Helper ───────────────────────────────────────────────────────────────────


def _mask(phone: str) -> str:
    """Return last-4-digits mask of a phone number."""
    return ("*" * (len(phone) - 4) + phone[-4:]) if len(phone) > 4 else phone


def get_provider_for_agency(agency: Agency):
    """Return the active SMSProvider adapter instance for the agency.

    Falls back to ConsoleSMSProvider when no active config exists.
    """
    from apps.messaging.models import AgencySMSConfig
    from apps.messaging.providers.console import ConsoleSMSProvider

    config = AgencySMSConfig.objects.filter(agency=agency, is_active=True).first()
    if config is None:
        return ConsoleSMSProvider()
    return config.get_provider_instance()


# ─── Enqueue ──────────────────────────────────────────────────────────────────


def enqueue_sms(
    agency: Agency,
    to: str,
    body: str,
    contact: Contact | None = None,
    template: SMSTemplate | None = None,
) -> SMSMessage:
    """
    Create an SMSMessage record in QUEUED state and dispatch the Celery send task.

    Returns the SMSMessage instance (pk is available).
    The actual HTTP call to the provider happens inside the Celery task.
    """
    from apps.messaging.models import AgencySMSConfig, SMSMessage, SMSProvider, sms_segment_count

    # Determine provider name for logging
    config = AgencySMSConfig.objects.filter(agency=agency, is_active=True).first()
    provider_name = config.provider if config else SMSProvider.CONSOLE

    msg = SMSMessage.objects.create(
        agency=agency,
        template=template,
        recipient_masked=_mask(to),
        body=body,
        provider=provider_name,
        segment_count=sms_segment_count(body),
        contact=contact,
    )

    # Import here to avoid circular imports at module level
    from apps.messaging.tasks import send_sms_task

    send_sms_task.delay(msg.pk, to)
    return msg


# ─── Send (called by Celery task) ─────────────────────────────────────────────


def send_sms_message(sms_id: int, to: str) -> None:
    """
    Perform the actual HTTP send to the provider and update SMSMessage state.

    Called from the Celery task (apps.messaging.tasks.send_sms_task).
    Raises on error so Celery can retry.
    """
    from apps.messaging.models import SMSMessage, SMSMessageState

    msg = SMSMessage.objects.select_related("agency").get(pk=sms_id)

    if msg.state not in (SMSMessageState.QUEUED, SMSMessageState.FAILED):
        # Already sent / delivered — idempotent guard
        return

    provider = get_provider_for_agency(msg.agency)
    try:
        provider_msg_id = provider.send(to=to, text=msg.body)
        msg.provider_message_id = provider_msg_id
        msg.state = SMSMessageState.SENT
        msg.sent_at = timezone.now()
        msg.save(update_fields=["state", "provider_message_id", "sent_at"])
        logger.info("SMS #%d sent id=%s", sms_id, provider_msg_id)
    except Exception as exc:
        msg.state = SMSMessageState.FAILED
        msg.failed_at = timezone.now()
        msg.failure_reason = str(exc)[:255]
        msg.save(update_fields=["state", "failed_at", "failure_reason"])
        logger.error("SMS #%d failed: %s", sms_id, exc)
        raise  # Let Celery retry
