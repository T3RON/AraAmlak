"""
Tests for phase 1A geo models: City, Neighborhood, NeighborhoodAdjacency,
Feature, Listing (new fields), ListingStatusHistory — no PostGIS required.

Covers:
- City: unique constraint (name, province)
- Neighborhood: unique constraint (city, name)
- NeighborhoodAdjacency: unique constraint
- Feature: unique name
- Listing.neighborhood FK: optional
- Listing.features M2M
- Listing CheckConstraint: floor <= total_floors
- ListingStatusHistory: records status changes
- Listing.location is text field in no-GIS env
"""

import pytest

from apps.listings.models import (
    City,
    DealType,
    Feature,
    Listing,
    ListingStatus,
    ListingStatusHistory,
    Neighborhood,
    NeighborhoodAdjacency,
    PropertyType,
)

pytestmark = pytest.mark.django_db


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_city(name="تهران", province="تهران"):
    return City.objects.create(name=name, province=province, slug=f"{name}-{province}")


def make_neighborhood(city, name="سعادت‌آباد"):
    return Neighborhood.objects.create(city=city, name=name)


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


# ─── City ─────────────────────────────────────────────────────────────────────


def test_city_created(db):
    city = make_city()
    assert city.pk is not None
    assert str(city) == "تهران (تهران)"


def test_city_unique_name_province(db):
    from django.db import IntegrityError
    make_city("مشهد", "خراسان رضوی")
    with pytest.raises(IntegrityError):
        make_city("مشهد", "خراسان رضوی")


# ─── Neighborhood ─────────────────────────────────────────────────────────────


def test_neighborhood_created(db):
    city = make_city()
    nh = make_neighborhood(city)
    assert nh.pk is not None
    assert str(nh) == "سعادت‌آباد — تهران"


def test_neighborhood_unique_per_city(db):
    from django.db import IntegrityError
    city = make_city()
    make_neighborhood(city, "ونک")
    with pytest.raises(IntegrityError):
        make_neighborhood(city, "ونک")


def test_neighborhood_aliases(db):
    city = make_city()
    nh = Neighborhood.objects.create(
        city=city,
        name="سعادت‌آباد",
        aliases=["سعادت آباد", "Saadat Abad"],
    )
    assert "سعادت آباد" in nh.aliases


# ─── NeighborhoodAdjacency ────────────────────────────────────────────────────


def test_adjacency_created(db):
    city = make_city()
    nh1 = make_neighborhood(city, "سعادت‌آباد")
    nh2 = make_neighborhood(city, "شهرک غرب")
    adj = NeighborhoodAdjacency.objects.create(
        from_neighborhood=nh1, to_neighborhood=nh2
    )
    assert adj.pk is not None


def test_adjacency_unique(db):
    from django.db import IntegrityError
    city = make_city()
    nh1 = make_neighborhood(city, "سعادت‌آباد")
    nh2 = make_neighborhood(city, "شهرک غرب")
    NeighborhoodAdjacency.objects.create(from_neighborhood=nh1, to_neighborhood=nh2)
    with pytest.raises(IntegrityError):
        NeighborhoodAdjacency.objects.create(from_neighborhood=nh1, to_neighborhood=nh2)


# ─── Feature ─────────────────────────────────────────────────────────────────


def test_feature_created(db):
    f = Feature.objects.create(name="آسانسور", icon="elevator")
    assert str(f) == "آسانسور"


def test_feature_unique_name(db):
    from django.db import IntegrityError
    Feature.objects.create(name="پارکینگ")
    with pytest.raises(IntegrityError):
        Feature.objects.create(name="پارکینگ")


# ─── Listing new fields ────────────────────────────────────────────────────────


def test_listing_neighborhood_fk(agency, db):
    city = make_city()
    nh = make_neighborhood(city)
    listing = make_listing(agency, neighborhood=nh)
    assert listing.neighborhood == nh


def test_listing_features_m2m(agency, db):
    f1 = Feature.objects.create(name="آسانسور")
    f2 = Feature.objects.create(name="پارکینگ")
    listing = make_listing(agency)
    listing.features.set([f1, f2])
    assert listing.features.count() == 2


def test_listing_floor_lte_total_floors_ok(agency, db):
    """floor=3, total_floors=5 should be valid."""
    listing = make_listing(agency, floor=3, total_floors=5)
    assert listing.floor == 3


def test_listing_floor_gt_total_floors_raises(agency, db):
    """floor=6, total_floors=5 should violate CheckConstraint."""
    from django.db import IntegrityError
    with pytest.raises(IntegrityError):
        make_listing(agency, floor=6, total_floors=5)


def test_listing_no_floor_no_constraint(agency, db):
    """floor=None: no constraint check."""
    listing = make_listing(agency, floor=None, total_floors=5)
    assert listing.total_floors == 5


# ─── ListingStatusHistory ─────────────────────────────────────────────────────


def test_status_history_created(agency, db):
    listing = make_listing(agency, status=ListingStatus.ACTIVE)
    hist = ListingStatusHistory.objects.create(
        listing=listing,
        old_status=ListingStatus.DRAFT,
        new_status=ListingStatus.ACTIVE,
    )
    assert hist.pk is not None
    assert "→" in str(hist)


def test_listing_location_is_textfield_without_gis(agency, db):
    """In no-GIS environment, location is a plain TextField."""
    listing = make_listing(agency)
    listing.location = "POINT(51.4 35.7)"
    listing.save()
    listing.refresh_from_db()
    assert "51.4" in listing.location
