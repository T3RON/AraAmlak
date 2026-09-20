"""Celery tasks for the matching app."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_matching_for_request(self, request_id: int) -> dict:
    """
    Find and persist matches for a single CRM Request.

    Triggered automatically via post_save signal after a Request is saved.
    Retries up to 3 times on transient errors.
    """
    from apps.crm.models import Request

    try:
        crm_request = Request.all_objects.select_related("agency").get(pk=request_id)
    except Request.DoesNotExist:
        logger.warning("run_matching_for_request: Request %s not found", request_id)
        return {"status": "not_found", "request_id": request_id}

    from apps.matching.services import find_matches

    matches = find_matches(crm_request)
    return {"status": "ok", "request_id": request_id, "match_count": len(matches)}
