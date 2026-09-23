"""
Console / Fake SMS adapter — for development and testing.

Behaviour:
- send()   : prints to stdout; returns a deterministic fake message ID.
- status() : always returns "delivered".
- balance(): returns Decimal("999999").

Set SMS_BACKEND = "apps.messaging.providers.console.ConsoleSMSProvider"
in your settings to use this adapter.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from .base import SMSProvider

logger = logging.getLogger(__name__)

_counter = 0


def _next_id() -> str:
    global _counter
    _counter += 1
    return f"FAKE-{_counter:06d}"


class ConsoleSMSProvider(SMSProvider):
    """
    Logs the SMS to the console.  Never sends a real message.
    Useful for local development and automated tests.
    """

    def send(self, to: str, text: str, sender: str | None = None) -> str:
        msg_id = _next_id()
        # Mask all but last 4 digits of recipient number
        masked = ("*" * (len(to) - 4) + to[-4:]) if len(to) > 4 else to
        logger.info("[SMS-CONSOLE] to=%s id=%s text=%r", masked, msg_id, text)
        return msg_id

    def status(self, message_id: str) -> str:
        return "delivered"

    def balance(self) -> Decimal:
        return Decimal("999999")
