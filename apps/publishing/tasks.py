"""Celery tasks for the publishing app."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def publish_listing_task(self, listing_id: int, config_id: int) -> dict:
    """
    Publish a listing to a portal asynchronously.

    Retries up to 3 times on transient errors (network, timeout).
    The service itself handles DB state; this task only dispatches and handles retries.
    """
    from apps.publishing.services import publish_listing

    try:
        job = publish_listing(listing_id, config_id)
        return {
            "status": job.status,
            "job_id": job.pk,
            "external_id": job.external_id,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "publish_listing_task error listing=%s config=%s: %s",
            listing_id,
            config_id,
            exc,
        )
        # Retry only on non-business errors (unexpected exceptions)
        raise self.retry(exc=exc) from exc
