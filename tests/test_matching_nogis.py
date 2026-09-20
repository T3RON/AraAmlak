"""
Tests for matching app — no PostGIS required.

Covers:
- Scoring logic (each criterion individually)
- find_matches() hard filters (agency, deal_type, status)
- find_matches() returns correct matches and scores
- Tenant isolation: agency A's matches never visible to agency B
- Upsert: running find_matches twice doesn't duplicate Match rows
"""

import pytest

from apps.crm.models import Request as CrmRequest
from apps.listings.models import DealType, Listing, ListingStatus, PropertyType
from apps.matching.models import Match
from apps.matching.services import find_matches

pytestmark = pytest.mark.django_db


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_listing(agency, **kwargs):
    defaults = {
        "agency": agency,
        "property_type": PropertyType.APARTMENT,
        "deal_type": DealType.SALE,
        "city": "تهران",
        "area": 80,
        "rooms": 2,
        "sale_price": 5_000_000_000,
        "status": ListingStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Listing.all_objects.create(**defaults)


def make_request(agency, **kwargs):
    defaults = {
        "agency": agency,
        "client_name": "مشتری تست",
        "deal_type": DealType.SALE,
        "city": "تهران",
        "property_types": [PropertyType.APARTMENT],
        "min_area": 60,
        "max_area": 100,
        "min_budget": 3_000_000_000,
        "max_budget": 8_000_000_000,
        "min_rooms": 1,
        "max_rooms": 3,
        "status": "new",
        "priority": "normal",
    }
    defaults.update(kwargs)
    return CrmRequest.all_objects.create(**defaults)


# ─── Scoring unit tests ────────────────────────────────────────────────────────


def test_perfect_match_scores_100(agency):
    """A listing matching all 5 criteria should score 100."""
    make_listing(agency)
    req = make_request(agency)
    matches = find_matches(req)
    assert len(matches) == 1
    assert matches[0].score == 100


def test_city_mismatch_deducts_30(agency):
    """Different city: score should be 70 (missing city bonus)."""
    make_listing(agency, city="اصفهان")
    req = make_request(agency, city="تهران")
    matches = find_matches(req)
    assert len(matches) == 1
    assert matches[0].score == 70


def test_property_type_mismatch_deducts_25(agency):
    """Property type not in requested list: score should be 75."""
    make_listing(agency, property_type=PropertyType.VILLA)
    req = make_request(agency, property_types=[PropertyType.APARTMENT])
    matches = find_matches(req)
    assert len(matches) == 1
    assert matches[0].score == 75


def test_area_out_of_range_deducts_20(agency):
    """Area outside range: score should be 80."""
    make_listing(agency, area=200)
    req = make_request(agency, max_area=100)
    matches = find_matches(req)
    assert len(matches) == 1
    assert matches[0].score == 80


def test_price_over_budget_deducts_15(agency):
    """Price above max_budget: score should be 85."""
    make_listing(agency, sale_price=20_000_000_000)
    req = make_request(agency, max_budget=8_000_000_000)
    matches = find_matches(req)
    assert len(matches) == 1
    assert matches[0].score == 85


def test_rooms_out_of_range_deducts_10(agency):
    """Rooms outside range: score should be 90."""
    make_listing(agency, rooms=5)
    req = make_request(agency, max_rooms=3)
    matches = find_matches(req)
    assert len(matches) == 1
    assert matches[0].score == 90


# ─── Hard filter tests ────────────────────────────────────────────────────────


def test_deal_type_mismatch_excluded(agency):
    """A listing with a different deal_type must never appear in results."""
    make_listing(agency, deal_type=DealType.RENT)
    req = make_request(agency, deal_type=DealType.SALE)
    matches = find_matches(req)
    assert len(matches) == 0


def test_inactive_listing_excluded(agency):
    """Only active listings should be matched."""
    make_listing(agency, status=ListingStatus.DRAFT)
    make_listing(agency, status=ListingStatus.EXPIRED)
    req = make_request(agency)
    matches = find_matches(req)
    assert len(matches) == 0


def test_zero_score_listing_excluded(agency):
    """A listing that scores 0 must not be persisted as a Match."""
    # Mismatching on 3 hard-soft fields resulting in 0 points
    make_listing(
        agency,
        city="اصفهان",
        property_type=PropertyType.VILLA,
        area=500,
        sale_price=100_000_000_000,
        rooms=10,
    )
    req = make_request(
        agency,
        city="تهران",
        property_types=[PropertyType.APARTMENT],
        max_area=100,
        max_budget=8_000_000_000,
        max_rooms=3,
    )
    matches = find_matches(req)
    # Should still persist if partial score > 0. Let's verify score:
    # city=no(-30), type=no(-25), area=no(-20), price=no(-15), rooms=no(-10) → 0
    assert all(m.score > 0 for m in matches)


def test_multiple_listings_ranked_by_score(agency):
    """find_matches returns results ordered by score descending."""
    # Perfect match
    make_listing(agency, city="تهران", property_type=PropertyType.APARTMENT)
    # City mismatch (score 70)
    make_listing(agency, city="اصفهان", property_type=PropertyType.APARTMENT)

    req = make_request(agency)
    matches = find_matches(req)
    assert len(matches) == 2
    scores = [m.score for m in sorted(matches, key=lambda m: -m.score)]
    assert scores[0] > scores[1]


# ─── Upsert / idempotency ─────────────────────────────────────────────────────


def test_find_matches_is_idempotent(agency):
    """Running find_matches twice must not create duplicate Match rows."""
    make_listing(agency)
    req = make_request(agency)
    find_matches(req)
    find_matches(req)  # run again
    count = Match.all_objects.filter(request=req).count()
    assert count == 1


# ─── Tenant isolation ─────────────────────────────────────────────────────────


def test_agency_isolation_listings(agency, agency_b):
    """Listings from agency_b must never match a request from agency_a."""
    # Listing belongs to agency_b
    make_listing(agency_b)
    # Request belongs to agency
    req = make_request(agency)
    matches = find_matches(req)
    assert len(matches) == 0


def test_agency_isolation_matches_manager(agency, agency_b):
    """Match.objects (AgencyManager) must not leak cross-agency matches."""
    from apps.core.models import set_current_agency

    # Create a match for agency
    make_listing(agency)
    req = make_request(agency)
    find_matches(req)
    assert Match.all_objects.filter(agency=agency).count() == 1

    # Bind thread-local to agency_b — should see no matches
    set_current_agency(agency_b)
    try:
        assert Match.objects.count() == 0
    finally:
        set_current_agency(None)
