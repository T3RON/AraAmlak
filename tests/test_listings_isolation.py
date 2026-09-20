"""
Tenant isolation tests for listings — requires PostGIS/Docker.

Run with: pytest -m "not nogis" --ds=ara_amlak.settings.testing
"""

import pytest

from apps.core.models import set_current_agency
from apps.listings.models import DealType, Listing, PropertyType


@pytest.mark.django_db
class TestListingTenantIsolation:
    """Verify AgencyManager prevents cross-tenant data leaks."""

    def test_manager_filters_by_current_agency(self, agency, agency_b):
        """Objects manager must only return listings for the active agency."""
        l_a = Listing.all_objects.create(
            agency=agency,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
        )
        l_b = Listing.all_objects.create(
            agency=agency_b,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
        )

        set_current_agency(agency)
        try:
            qs = Listing.objects.all()
            pks = list(qs.values_list("pk", flat=True))
            assert l_a.pk in pks
            assert l_b.pk not in pks
        finally:
            set_current_agency(None)

    def test_all_objects_bypasses_filter(self, agency, agency_b):
        """all_objects must return listings from all agencies."""
        l_a = Listing.all_objects.create(
            agency=agency,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
        )
        l_b = Listing.all_objects.create(
            agency=agency_b,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
        )

        set_current_agency(agency)
        try:
            pks = list(Listing.all_objects.values_list("pk", flat=True))
            assert l_a.pk in pks
            assert l_b.pk in pks
        finally:
            set_current_agency(None)

    def test_no_context_returns_all(self, agency, agency_b):
        """Without a thread-local agency, objects manager returns all rows."""
        set_current_agency(None)
        l_a = Listing.all_objects.create(
            agency=agency,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
        )
        l_b = Listing.all_objects.create(
            agency=agency_b,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
        )
        pks = list(Listing.objects.values_list("pk", flat=True))
        assert l_a.pk in pks
        assert l_b.pk in pks
