"""
Celery tasks for the accounts app.

SMS sending is a stub in phase 1.
Real SMS provider integration (with official API docs) is deferred to a later phase.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="accounts.send_otp_sms")
def send_otp_sms_task(phone: str) -> None:
    """
    Send OTP SMS to the given phone number.

    STUB: In phase 1, this task only logs that it would send an SMS.
    The actual OTP code is NOT passed to this task — it is read from
    Redis inside the SMS provider client (to be implemented in a later phase).

    Phase 2 will read official SMS provider API docs and implement this properly.
    """
    # Log only last 4 digits — never log the full phone in production
    logger.info("SMS OTP task triggered for phone ending in ...%s", phone[-4:])
    # TODO(phase-2): Implement real SMS provider call here
