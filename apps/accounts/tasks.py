"""
Celery tasks for the accounts app.

Phase 4A: OTP SMS is now sent via the messaging app's provider infrastructure.
For agencies without a config, the ConsoleSMSProvider is used as fallback.
"""

import logging

from django.core.cache import cache

from celery import shared_task

logger = logging.getLogger(__name__)

_OTP_PREFIX = "otp:"


@shared_task(name="accounts.send_otp_sms", max_retries=3, acks_late=True)
def send_otp_sms_task(phone: str) -> None:
    """
    Send OTP SMS to the given phone number.

    Reads the hashed OTP from Redis (stored by otp.send_otp()) and sends it
    via the ConsoleSMSProvider (no agency context for OTP — use console/fallback).
    """
    from apps.messaging.providers.console import ConsoleSMSProvider

    code = cache.get(f"{_OTP_PREFIX}{phone}")
    if code is None:
        logger.warning("send_otp_sms_task: OTP already expired for phone ...%s", phone[-4:])
        return

    provider = ConsoleSMSProvider()
    try:
        body = f"کد تأیید آرا املاک: {code}"
        provider.send(to=phone, text=body)
        logger.info("OTP SMS sent for phone ending ...%s", phone[-4:])
    except Exception as exc:
        logger.error("OTP SMS send failed for ...%s: %s", phone[-4:], exc)
        raise
