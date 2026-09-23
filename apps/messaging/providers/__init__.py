"""
SMS provider adapters.

Everything in this package is pure Python (no Django import) so it can be
unit-tested with a mocked HTTP transport.
"""

from apps.messaging.providers.base import (  # noqa: F401
    BalanceResult,
    DeliveryState,
    SendResult,
    SMSProvider,
    SMSProviderError,
    StatusResult,
    mask_phone,
)
from apps.messaging.providers.registry import PROVIDER_CHOICES, build_provider  # noqa: F401
