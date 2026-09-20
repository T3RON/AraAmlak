"""
Listings Celery tasks.
"""

from celery import shared_task


@shared_task(name="listings.expire_overdue_listings")
def expire_overdue_listings_task():
    """Periodic task: mark listings with passed expires_at as expired."""
    from apps.listings.services import expire_overdue_listings

    return expire_overdue_listings()
