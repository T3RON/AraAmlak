"""
Matching service: find_matches(request) → list[Match]

Scoring rubric (max 100):
  city match            +30
  property_type match   +25
  area in range         +20
  price in range        +15
  rooms in range        +10
"""

import logging
from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from apps.crm.models import Request

logger = logging.getLogger(__name__)

# Score weights
SCORE_CITY = 30
SCORE_PROPERTY_TYPE = 25
SCORE_AREA = 20
SCORE_PRICE = 15
SCORE_ROOMS = 10


def _score_listing(listing, crm_request: "Request") -> int:
    """Compute a match score (0–100) for a single listing against a request."""
    score = 0

    # City match
    if crm_request.city and listing.city:
        if listing.city.strip() == crm_request.city.strip():
            score += SCORE_CITY

    # Property type in requested types
    if crm_request.property_types and listing.property_type:
        if listing.property_type in crm_request.property_types:
            score += SCORE_PROPERTY_TYPE

    # Area in range
    if listing.area is not None:
        area_ok = True
        if crm_request.min_area is not None and listing.area < crm_request.min_area:
            area_ok = False
        if crm_request.max_area is not None and listing.area > crm_request.max_area:
            area_ok = False
        if area_ok:
            score += SCORE_AREA

    # Price in budget
    price = _get_relevant_price(listing, crm_request.deal_type)
    if price is not None:
        price_ok = True
        if crm_request.min_budget is not None and price < crm_request.min_budget:
            price_ok = False
        if crm_request.max_budget is not None and price > crm_request.max_budget:
            price_ok = False
        if price_ok:
            score += SCORE_PRICE

    # Rooms in range
    if listing.rooms is not None:
        rooms_ok = True
        if crm_request.min_rooms is not None and listing.rooms < crm_request.min_rooms:
            rooms_ok = False
        if crm_request.max_rooms is not None and listing.rooms > crm_request.max_rooms:
            rooms_ok = False
        if rooms_ok:
            score += SCORE_ROOMS

    return score


def _get_relevant_price(listing, deal_type: str):
    """Return the price field relevant for the given deal_type."""
    from apps.listings.models import DealType

    if deal_type == DealType.SALE:
        return listing.sale_price
    if deal_type in (DealType.RENT, DealType.MORTGAGE_RENT):
        return listing.rent_amount
    return listing.sale_price


def find_matches(crm_request: "Request") -> list:
    """
    Find and persist all matching listings for a Request.

    Hard filters (mandatory):
      - same agency (tenant isolation)
      - same deal_type
      - status = active

    Returns the list of Match objects created/updated (score > 0).
    """
    from apps.listings.models import Listing, ListingStatus
    from apps.matching.models import Match

    # Hard-filter candidates
    candidates = Listing.all_objects.filter(
        agency=crm_request.agency,
        deal_type=crm_request.deal_type,
        status=ListingStatus.ACTIVE,
    )

    matched = []
    to_create = []
    to_update_ids = []
    score_map = {}

    for listing in candidates:
        score = _score_listing(listing, crm_request)
        if score > 0:
            score_map[listing.pk] = score

    if not score_map:
        return []

    # Upsert: update existing, create new
    existing = {
        m.listing_id: m
        for m in Match.all_objects.filter(
            request=crm_request, listing_id__in=score_map.keys()
        )
    }

    with transaction.atomic():
        for listing_pk, score in score_map.items():
            if listing_pk in existing:
                m = existing[listing_pk]
                if m.score != score:
                    m.score = score
                    to_update_ids.append(m)
                matched.append(m)
            else:
                to_create.append(
                    Match(
                        agency=crm_request.agency,
                        request=crm_request,
                        listing_id=listing_pk,
                        score=score,
                    )
                )

        if to_create:
            created = Match.all_objects.bulk_create(to_create)
            matched.extend(created)

        if to_update_ids:
            Match.all_objects.bulk_update(to_update_ids, ["score"])

    logger.info(
        "Matching: request=%s → %d matches (%d new, %d updated)",
        crm_request.pk,
        len(matched),
        len(to_create),
        len(to_update_ids),
    )
    return matched
