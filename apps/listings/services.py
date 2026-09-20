"""
Listings service layer.

All business logic for creating, updating, and expiring listings lives here.
Views must only call these functions — never manipulate ORM directly.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def create_listing(agency, data: dict[str, Any], user=None):
    """
    Create a new Listing for *agency* from validated *data*.

    Returns the saved Listing instance.
    Called from views; never import into Celery tasks.
    """
    from apps.listings.models import Listing  # avoid circular at module level

    with transaction.atomic():
        listing = Listing(agency=agency, **data)
        if user is not None and not listing.assigned_to_id:
            listing.assigned_to = user
        listing.save()
        logger.info("Listing created: pk=%s agency=%s", listing.pk, agency.pk)
    return listing


def update_listing(listing, data: dict[str, Any]) -> None:
    """
    Update *listing* fields from *data* dict and save.

    Only updates the fields present in *data*.
    """
    for field, value in data.items():
        setattr(listing, field, value)
    listing.save(update_fields=list(data.keys()) + ["updated_at"])
    logger.info("Listing updated: pk=%s", listing.pk)


def change_listing_status(listing, new_status: str) -> None:
    """
    Change the status of a listing.

    If status transitions to 'sold' or 'expired', clears expires_at.
    """
    from apps.listings.models import ListingStatus

    listing.status = new_status
    if new_status in (ListingStatus.SOLD, ListingStatus.EXPIRED):
        listing.expires_at = None
    listing.save(update_fields=["status", "expires_at", "updated_at"])
    logger.info("Listing %s status → %s", listing.pk, new_status)


def expire_overdue_listings() -> int:
    """
    Mark all active listings whose expires_at has passed as 'expired'.

    Called from Celery Beat. Returns count of expired listings.
    """
    from apps.listings.models import Listing, ListingStatus

    now = timezone.now()
    qs = Listing.all_objects.filter(
        status=ListingStatus.ACTIVE,
        expires_at__lt=now,
    )
    count = qs.update(status=ListingStatus.EXPIRED)
    if count:
        logger.info("Expired %d overdue listings", count)
    return count
