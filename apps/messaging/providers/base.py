"""
SMSProvider — abstract interface all SMS adapters must implement.

Design:
- send()      → returns provider_message_id (str)
- status()    → returns current delivery status string
- balance()   → returns remaining credit as Decimal
- send_bulk() → optional; default loops over send()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal


class SMSProvider(ABC):
    """Abstract base for all SMS provider adapters."""

    @abstractmethod
    def send(self, to: str, text: str, sender: str | None = None) -> str:
        """
        Send a single SMS.

        Parameters
        ----------
        to     : recipient number (MSISDN, e.g. "09121234567")
        text   : message body (UTF-8, may be Persian)
        sender : optional line number; falls back to provider default

        Returns
        -------
        provider_message_id  (str)  — unique ID from the provider
        """

    @abstractmethod
    def status(self, message_id: str) -> str:
        """Query delivery status; returns a provider-specific status string."""

    @abstractmethod
    def balance(self) -> Decimal:
        """Return remaining account credit as Decimal (Tomans/Rials/units)."""

    def send_bulk(self, recipients: list[str], text: str, sender: str | None = None) -> list[str]:
        """
        Send the same text to multiple recipients.

        Default implementation loops over send(); override for providers
        that have a native bulk endpoint.

        Returns list of provider_message_ids in the same order as recipients.
        """
        return [self.send(to, text, sender) for to in recipients]
