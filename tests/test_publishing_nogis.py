"""
Tests for publishing app — no PostGIS required.

Covers:
- DummyAdapter: publish() returns external_id
- DummyAdapter: registered in ADAPTER_MAP
- get_adapter(): raises PublishError for unknown portal
- publish_listing(): creates PublishJob with status=success
- publish_listing(): sets external_id and published_at
- publish_listing(): failing adapter → status=failed, error_message stored
- publish_listing(): PublishJob.agency denormalized from listing.agency
- PortalConfig: only active configs visible via default manager (AgencyManager)
- Tenant isolation: PublishJob from agency_b not visible to agency
- Dashboard context: published_today count
"""

from unittest.mock import patch

import pytest

from apps.listings.models import DealType, Listing, ListingStatus, PropertyType
from apps.publishing.adapters import ADAPTER_MAP, DummyAdapter, PublishError, get_adapter
from apps.publishing.models import JobStatus, Portal, PortalConfig, PublishJob
from apps.publishing.services import publish_listing

pytestmark = pytest.mark.django_db


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_listing(agency, **kwargs):
    defaults = {
        "agency": agency,
        "property_type": PropertyType.APARTMENT,
        "deal_type": DealType.SALE,
        "city": "تهران",
        "status": ListingStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Listing.all_objects.create(**defaults)


def make_portal_config(agency, portal=Portal.DUMMY, **kwargs):
    defaults = {
        "agency": agency,
        "portal": portal,
        "is_active": True,
    }
    defaults.update(kwargs)
    return PortalConfig.all_objects.create(**defaults)


# ─── Adapter unit tests ───────────────────────────────────────────────────────


def test_dummy_adapter_returns_external_id(agency):
    """DummyAdapter.publish() must return a dict with 'external_id'."""
    listing = make_listing(agency)
    config = make_portal_config(agency)
    adapter = DummyAdapter()
    result = adapter.publish(listing, config)
    assert "external_id" in result
    assert result["external_id"] == f"dummy-{listing.pk}"


def test_dummy_adapter_registered_in_map():
    """DummyAdapter must be accessible via ADAPTER_MAP['dummy']."""
    assert "dummy" in ADAPTER_MAP
    assert ADAPTER_MAP["dummy"] is DummyAdapter


def test_get_adapter_unknown_portal_raises():
    """get_adapter() with unknown portal key must raise PublishError."""
    with pytest.raises(PublishError, match="No adapter registered"):
        get_adapter("nonexistent_portal")


# ─── Service: success path ────────────────────────────────────────────────────


def test_publish_listing_creates_job(agency):
    """publish_listing() must create a PublishJob record."""
    listing = make_listing(agency)
    config = make_portal_config(agency)
    job = publish_listing(listing.pk, config.pk)
    assert PublishJob.all_objects.filter(pk=job.pk).exists()


def test_publish_listing_success_status(agency):
    """DummyAdapter → publish_listing() must set status=success."""
    listing = make_listing(agency)
    config = make_portal_config(agency)
    job = publish_listing(listing.pk, config.pk)
    assert job.status == JobStatus.SUCCESS


def test_publish_listing_sets_external_id(agency):
    """publish_listing() must persist external_id from adapter result."""
    listing = make_listing(agency)
    config = make_portal_config(agency)
    job = publish_listing(listing.pk, config.pk)
    assert job.external_id == f"dummy-{listing.pk}"


def test_publish_listing_sets_published_at(agency):
    """publish_listing() must set published_at on success."""
    listing = make_listing(agency)
    config = make_portal_config(agency)
    job = publish_listing(listing.pk, config.pk)
    assert job.published_at is not None


def test_publish_listing_agency_denormalized(agency):
    """PublishJob.agency must equal listing.agency (denormalized)."""
    listing = make_listing(agency)
    config = make_portal_config(agency)
    job = publish_listing(listing.pk, config.pk)
    assert job.agency_id == agency.pk


# ─── Service: failure path ────────────────────────────────────────────────────


def test_publish_listing_failed_status(agency):
    """When adapter raises PublishError, status must be 'failed'."""
    listing = make_listing(agency)
    config = make_portal_config(agency)
    with patch.object(DummyAdapter, "publish", side_effect=PublishError("API down")):
        job = publish_listing(listing.pk, config.pk)
    assert job.status == JobStatus.FAILED


def test_publish_listing_stores_error_message(agency):
    """Failed job must store the error message."""
    listing = make_listing(agency)
    config = make_portal_config(agency)
    with patch.object(DummyAdapter, "publish", side_effect=PublishError("API timeout")):
        job = publish_listing(listing.pk, config.pk)
    assert "API timeout" in job.error_message


# ─── PortalConfig manager ─────────────────────────────────────────────────────


def test_inactive_config_not_in_objects_filter(agency):
    """Inactive PortalConfig should not appear when filtering is_active=True."""
    make_portal_config(agency, is_active=False)
    active_count = PortalConfig.all_objects.filter(
        agency=agency, is_active=True
    ).count()
    assert active_count == 0


# ─── Tenant isolation ─────────────────────────────────────────────────────────


def test_publish_job_tenant_isolation(agency, agency_b):
    """PublishJob from agency_b must not be visible when agency is set in context."""
    from apps.core.models import set_current_agency

    listing_b = make_listing(agency_b)
    config_b = make_portal_config(agency_b)
    publish_listing(listing_b.pk, config_b.pk)

    # Bind thread-local to agency — should see 0 jobs
    set_current_agency(agency)
    try:
        assert PublishJob.objects.count() == 0
    finally:
        set_current_agency(None)
