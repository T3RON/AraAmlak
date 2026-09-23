"""
Listings Celery tasks.
"""

from celery import shared_task


@shared_task(
    name="listings.run_import_job",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def run_import_job_task(self, import_job_id: int) -> dict:
    """Process an ImportJob: parse Excel/CSV and create Listing records."""
    from apps.listings.import_service import run_import_job  # noqa: PLC0415

    try:
        return run_import_job(import_job_id)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc) from exc



@shared_task(name="listings.expire_overdue_listings")
def expire_overdue_listings_task():
    """Periodic task: mark listings with passed expires_at as expired."""
    from apps.listings.services import expire_overdue_listings

    return expire_overdue_listings()


@shared_task(
    name="listings.process_media",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def process_media_task(self, media_id: int) -> dict:
    """
    Process a photo Media record: strip EXIF, generate thumbnail + WebP.
    Retries up to 3 times on transient errors.
    """
    from apps.listings.media_services import process_photo  # noqa: PLC0415

    try:
        process_photo(media_id)
        return {"media_id": media_id, "status": "ok"}
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc) from exc
