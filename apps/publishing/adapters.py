"""
Publishing adapters — adapter pattern for portal integrations.

Each portal has its own adapter class.
The DummyAdapter is used for testing and local development.

To add a new portal:
1. Create a new class inheriting BasePortalAdapter
2. Override publish()
3. Register in ADAPTER_MAP

Note: Real portal adapters (Divar, Sheypoor) require official API credentials.
Per project constitution, never guess API endpoints — read official docs first.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.listings.models import Listing
    from apps.publishing.models import PortalConfig


# ─── Exceptions ───────────────────────────────────────────────────────────────


class PublishError(Exception):
    """Raised when a portal adapter fails to publish a listing."""


# ─── Base adapter ─────────────────────────────────────────────────────────────


class BasePortalAdapter:
    """
    Abstract base class for all portal adapters.

    Subclasses must implement `publish()`.
    `publish()` should return a dict with at least {"external_id": str}.
    On failure, raise PublishError with a descriptive message.
    """

    def publish(self, listing: Listing, config: PortalConfig) -> dict:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement publish()"
        )


# ─── Dummy adapter (testing / local dev) ──────────────────────────────────────


class DummyAdapter(BasePortalAdapter):
    """
    Always succeeds with a fake external_id.
    Used for development, testing, and demo environments.
    """

    def publish(self, listing: Listing, config: PortalConfig) -> dict:
        return {"external_id": f"dummy-{listing.pk}"}


# ─── Registry ─────────────────────────────────────────────────────────────────

ADAPTER_MAP: dict[str, type[BasePortalAdapter]] = {
    "dummy": DummyAdapter,
    # "divar": DivarAdapter,     ← implement after reading official API docs
    # "sheypoor": SheypoorAdapter,
}


def get_adapter(portal: str) -> BasePortalAdapter:
    """Return an instantiated adapter for the given portal key."""
    cls = ADAPTER_MAP.get(portal)
    if cls is None:
        raise PublishError(f"No adapter registered for portal: {portal!r}")
    return cls()
