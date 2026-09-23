"""SMSProvider interface and shared value objects."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class DeliveryState:
    """Provider-neutral delivery states (mapped onto SMSMessage.status)."""

    QUEUED = "queued"  # accepted by provider, not yet handed to operator
    SENT = "sent"  # handed to the operator / telecom
    DELIVERED = "delivered"  # delivery report received from handset
    FAILED = "failed"
    UNKNOWN = "unknown"  # provider could not tell (keep polling / keep state)


class SMSProviderError(Exception):
    """
    Raised by adapters. ``retryable`` tells the Celery task whether a retry
    with backoff makes sense (network error, 5xx, provider busy) or not
    (bad credentials, bad number, not enough credit).
    """

    def __init__(self, message: str, *, retryable: bool = False, code: str | int | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.code = code


@dataclass
class SendResult:
    provider_message_id: str
    state: str = DeliveryState.QUEUED
    cost_rial: int | None = None
    raw_status: str = ""


@dataclass
class StatusResult:
    provider_message_id: str
    state: str
    raw_status: str = ""


@dataclass
class BalanceResult:
    amount: float
    unit: str = "rial"  # "rial" or "sms" depending on panel type
    extra: dict = field(default_factory=dict)


def mask_phone(phone: str) -> str:
    """Only the last 4 digits ever reach logs: ``*******4567``."""
    phone = phone or ""
    if len(phone) <= 4:
        return "*" * len(phone)
    return "*" * (len(phone) - 4) + phone[-4:]


class SMSProvider(ABC):
    """
    Interface every SMS panel adapter implements.

    Implementations must never log the API key, password, full phone number or
    message body.
    """

    name: str = ""
    supports_bulk: bool = False

    def __init__(
        self, *, api_key: str = "", username: str = "", password: str = "", sender: str = ""
    ) -> None:
        self.api_key = api_key or ""
        self.username = username or ""
        self.password = password or ""
        self.sender = sender or ""

    @abstractmethod
    def send(self, to: str, text: str, *, local_id: str | None = None) -> SendResult:
        """Send one message. Raise SMSProviderError on failure."""

    @abstractmethod
    def status(self, provider_message_ids: list[str]) -> list[StatusResult]:
        """Return delivery state for previously sent messages."""

    @abstractmethod
    def balance(self) -> BalanceResult:
        """Return the remaining account credit."""

    def send_bulk(self, recipients: list[str], text: str) -> list[SendResult]:
        """Default: loop over ``send``. Adapters with a native bulk call override it."""
        return [self.send(to, text) for to in recipients]

    def test_connection(self) -> BalanceResult:
        """A cheap authenticated call; balance works for every provider we support."""
        return self.balance()

    def __repr__(self) -> str:  # never expose secrets in reprs / tracebacks
        return f"<{self.__class__.__name__} sender={self.sender!r}>"
