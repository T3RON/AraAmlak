"""
CRM service layer.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def create_request(agency, data: dict[str, Any], user=None):
    """
    Create a new CRM Request for *agency*.

    Returns the saved Request instance.
    """
    from apps.crm.models import Request

    with transaction.atomic():
        req = Request(agency=agency, **data)
        if user is not None and not req.assigned_to_id:
            req.assigned_to = user
        req.save()
        logger.info("CRM Request created: pk=%s agency=%s", req.pk, agency.pk)
    return req


def update_request(req, data: dict[str, Any]) -> None:
    """Update CRM request fields from *data* dict."""
    for field, value in data.items():
        setattr(req, field, value)
    req.save(update_fields=list(data.keys()) + ["updated_at"])
    logger.info("CRM Request updated: pk=%s", req.pk)


def close_request(req, *, cancelled: bool = False) -> None:
    """
    Close (or cancel) a CRM request.

    Sets status to 'closed' or 'cancelled' and records closed_at.
    """
    from apps.crm.models import RequestStatus

    req.status = RequestStatus.CANCELLED if cancelled else RequestStatus.CLOSED
    req.closed_at = timezone.now()
    req.save(update_fields=["status", "closed_at", "updated_at"])
    logger.info("CRM Request %s → %s", req.pk, req.status)
