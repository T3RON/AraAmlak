"""
OTP service: generate, store (Redis), verify OTP codes.

- Codes are stored in Redis with TTL.
- Codes are NEVER logged.
- Max attempt tracking prevents brute-force.
"""

from __future__ import annotations

import logging
import random
import string

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_OTP_PREFIX = "otp:"
_ATTEMPT_PREFIX = "otp_attempts:"


def _otp_key(phone: str) -> str:
    return f"{_OTP_PREFIX}{phone}"


def _attempt_key(phone: str) -> str:
    return f"{_ATTEMPT_PREFIX}{phone}"


def generate_otp() -> str:
    """Generate a random 6-digit numeric OTP code."""
    length = getattr(settings, "OTP_CODE_LENGTH", 6)
    return "".join(random.choices(string.digits, k=length))  # noqa: S311


def send_otp(phone: str) -> bool:
    """
    Generate and store OTP for the given phone number.
    Returns True on success.

    The actual SMS sending is delegated to a Celery task (stub in phase 1).
    The OTP code itself is NOT returned to the caller — it lives only in Redis.
    """
    ttl = getattr(settings, "OTP_TTL_SECONDS", 120)
    code = generate_otp()

    # Store code in Redis (do NOT log the code)
    cache.set(_otp_key(phone), code, timeout=ttl)
    # Reset attempt counter
    cache.delete(_attempt_key(phone))

    # Dispatch SMS task (imported here to avoid circular import)
    from apps.accounts.tasks import send_otp_sms_task  # noqa: PLC0415

    send_otp_sms_task.delay(phone)  # task receives phone; fetches nothing sensitive
    logger.info("OTP dispatched for phone ending in ...%s", phone[-4:])
    return True


def verify_otp(phone: str, code: str) -> bool:
    """
    Verify the OTP code for the given phone.
    Returns True if valid, False otherwise.
    Increments attempt counter; deletes code after max attempts.
    """
    max_attempts = getattr(settings, "OTP_MAX_ATTEMPTS", 5)
    stored_code = cache.get(_otp_key(phone))

    if stored_code is None:
        # Expired or never sent
        return False

    # Track attempts
    attempts = cache.get(_attempt_key(phone), 0) + 1
    ttl = getattr(settings, "OTP_TTL_SECONDS", 120)
    cache.set(_attempt_key(phone), attempts, timeout=ttl)

    if attempts > max_attempts:
        cache.delete(_otp_key(phone))
        cache.delete(_attempt_key(phone))
        logger.warning("OTP max attempts exceeded for phone ending in ...%s", phone[-4:])
        return False

    if stored_code == code:
        # Consume the code immediately
        cache.delete(_otp_key(phone))
        cache.delete(_attempt_key(phone))
        return True

    return False
