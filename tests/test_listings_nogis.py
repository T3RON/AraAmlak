"""
No-GIS tests for listings models and services.

Safe to run on Windows (SQLite) without PostGIS.
Tests: model creation, code generation, service functions, currency display.
"""

import pytest

from apps.listings.models import DealType, Listing, ListingStatus, PropertyType
from apps.listings.services import (
    change_listing_status,
    create_listing,
    expire_overdue_listings,
    update_listing,
)


@pytest.mark.django_db
class TestListingModel:
    def test_listing_creation_sets_defaults(self, agency):
        listing = Listing.all_objects.create(
            agency=agency,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
        )
        assert listing.status == ListingStatus.ACTIVE
        assert listing.rooms == 0
        assert listing.price_negotiable is True
        assert listing.parking is False

    def test_auto_code_generated(self, agency):
        listing = Listing.all_objects.create(
            agency=agency,
            property_type=PropertyType.VILLA,
            deal_type=DealType.RENT,
        )
        assert listing.code != ""
        assert "-" in listing.code

    def test_auto_code_unique_per_agency(self, agency):
        l1 = Listing.all_objects.create(
            agency=agency,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
        )
        l2 = Listing.all_objects.create(
            agency=agency,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
        )
        assert l1.code != l2.code

    def test_str_representation(self, agency):
        listing = Listing.all_objects.create(
            agency=agency,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
        )
        assert "آپارتمان" in str(listing)
        assert "فروش" in str(listing)

    def test_encrypted_owner_phone(self, agency):
        listing = Listing.all_objects.create(
            agency=agency,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
            owner_phone="09120000000",
        )
        # Value in DB is encrypted — fetch fresh from DB
        fresh = Listing.all_objects.get(pk=listing.pk)
        assert fresh.owner_phone == "09120000000"


@pytest.mark.django_db
class TestListingServices:
    def test_create_listing_service(self, agency, user):
        listing = create_listing(
            agency=agency,
            data={
                "property_type": PropertyType.APARTMENT,
                "deal_type": DealType.SALE,
                "city": "تهران",
                "area": 90,
                "rooms": 2,
            },
            user=user,
        )
        assert listing.pk is not None
        assert listing.agency == agency
        assert listing.city == "تهران"

    def test_create_listing_assigns_user(self, agency, user):
        listing = create_listing(
            agency=agency,
            data={"property_type": PropertyType.APARTMENT, "deal_type": DealType.SALE},
            user=user,
        )
        assert listing.assigned_to == user

    def test_update_listing_service(self, agency):
        listing = Listing.all_objects.create(
            agency=agency,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
            city="اصفهان",
        )
        update_listing(listing, {"city": "شیراز", "area": 120})
        listing.refresh_from_db()
        assert listing.city == "شیراز"
        assert listing.area == 120

    def test_change_listing_status(self, agency):
        listing = Listing.all_objects.create(
            agency=agency,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
        )
        change_listing_status(listing, ListingStatus.RESERVED)
        listing.refresh_from_db()
        assert listing.status == ListingStatus.RESERVED

    def test_expire_overdue_listings(self, agency):
        import datetime

        from django.utils import timezone

        past = timezone.now() - datetime.timedelta(days=1)
        l1 = Listing.all_objects.create(
            agency=agency,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
            status=ListingStatus.ACTIVE,
            expires_at=past,
        )
        l2 = Listing.all_objects.create(
            agency=agency,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
            status=ListingStatus.ACTIVE,
            expires_at=None,  # no expiry
        )
        count = expire_overdue_listings()
        assert count == 1
        l1.refresh_from_db()
        assert l1.status == ListingStatus.EXPIRED
        l2.refresh_from_db()
        assert l2.status == ListingStatus.ACTIVE
