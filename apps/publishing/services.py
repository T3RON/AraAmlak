"""
Publishing service — core business logic for publishing a listing to a portal.

All DB mutations and adapter calls happen here.
Views and Celery tasks call this service; they must not contain business logic.
"""

from __future__ import annotations

import logging

from django.utils import timezone

from apps.publishing.adapters import PublishError, get_adapter
from apps.publishing.models import JobStatus, PublishJob

logger = logging.getLogger(__name__)


def publish_listing(listing_id: int, config_id: int) -> PublishJob:
    """
    Publish a single listing to the portal described by config_id.

    Flow:
        1. Create a PublishJob with status=pending
        2. Mark it running
        3. Call the adapter
        4. On success: status=success, external_id set, published_at=now
        5. On failure: status=failed, error_message stored

    Returns the saved PublishJob instance.
    Raises ValueError if listing or config do not exist.
    """
    from apps.listings.models import Listing
    from apps.publishing.models import PortalConfig

    # Fetch objects (all_objects bypasses tenant filter — service is authoritative)
    listing = Listing.all_objects.get(pk=listing_id)
    config = PortalConfig.all_objects.get(pk=config_id)

    job = PublishJob.all_objects.create(
        agency=listing.agency,
        listing=listing,
        portal_config=config,
        status=JobStatus.PENDING,
    )

    # Mark running
    job.status = JobStatus.RUNNING
    job.save(update_fields=["status", "updated_at"])

    try:
        adapter = get_adapter(config.portal)
        result = adapter.publish(listing, config)
        job.status = JobStatus.SUCCESS
        job.external_id = result.get("external_id", "")
        job.published_at = timezone.now()
        job.error_message = ""
        logger.info(
            "Published listing %s to %s — external_id=%s",
            listing_id,
            config.portal,
            job.external_id,
        )
    except (PublishError, Exception) as exc:  # noqa: BLE001
        job.status = JobStatus.FAILED
        job.error_message = str(exc)
        logger.error(
            "Failed to publish listing %s to %s: %s",
            listing_id,
            config.portal,
            exc,
        )

    job.save(update_fields=["status", "external_id", "published_at", "error_message", "updated_at"])
    return job
