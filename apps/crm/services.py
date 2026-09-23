"""
CRM service layer.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

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


# ─── Timeline / Visit / Task / Notification ───────────────────────────────────────


def add_interaction(
    agency,
    user,
    kind: str,
    *,
    contact=None,
    listing=None,
    request=None,  # noqa: A002 — domain name shadows builtin in service API
    summary: str = "",
    detail: str = "",
    occurred_at=None,
    commit: bool = True,
):
    """
    Record a timeline Interaction.

    At least one of contact/listing/request is required (also enforced by DB constraint).
    The agency is taken from the target object to guarantee tenant safety.
    """
    from apps.crm.models import Interaction

    if not any([contact, listing, request]):
        raise ValueError("interaction requires at least one of contact/listing/request")

    interaction = Interaction(
        agency=agency,
        kind=kind,
        contact=contact,
        listing=listing,
        request=request,
        summary=summary or _("ثبت رویداد تایم‌لاین"),
        detail=detail,
        performed_by=user,
        occurred_at=occurred_at or timezone.now(),
    )
    if commit:
        interaction.save()
    return interaction


def get_timeline(*, contact=None, listing=None, request=None, kind: str | None = None):
    """
    Return the Interaction timeline for a target object (newest first).

    Exactly one of contact/listing/request is expected; passing none returns the
    agency-wide timeline.
    """
    from apps.crm.models import Interaction

    qs = Interaction.objects.all()
    if contact is not None:
        qs = qs.filter(contact=contact)
    if listing is not None:
        qs = qs.filter(listing=listing)
    if request is not None:
        qs = qs.filter(request=request)
    if kind:
        qs = qs.filter(kind=kind)
    return qs.select_related("performed_by", "contact", "listing", "request")


def schedule_visit(
    agency,
    user,
    *,
    listing,
    contact,
    scheduled_at,
    request=None,
    note: str = "",
    agent=None,
    commit: bool = True,
):
    """
    Schedule a Visit for *contact* on *listing* and record it on the timeline.

    Returns the (visit, interaction) pair.
    """
    from apps.crm.models import InteractionKind, Visit, VisitStatus

    visit = Visit(
        agency=agency,
        listing=listing,
        contact=contact,
        request=request,
        scheduled_at=scheduled_at,
        status=VisitStatus.SCHEDULED,
        note=note,
        agent=agent or user,
    )
    interaction = None
    if commit:
        with transaction.atomic():
            visit.save()
            interaction = add_interaction(
                agency,
                user,
                InteractionKind.VISIT,
                contact=contact,
                listing=listing,
                request=request,
                summary=_("قرار بازدید: {}").format(listing),
                detail=note,
                occurred_at=scheduled_at,
            )
    return visit, interaction


def complete_visit(visit, *, outcome: str, note: str = "", status: str | None = None):
    """
    Mark a Visit completed with *outcome*, set timestamps, and record the timeline event.
    """
    from apps.crm.models import InteractionKind, VisitStatus

    agency = visit.agency
    visit.status = status or VisitStatus.COMPLETED
    visit.outcome = outcome
    visit.completed_at = timezone.now()
    if note:
        visit.note = note
    with transaction.atomic():
        visit.save(
            update_fields=[
                "status",
                "outcome",
                "completed_at",
                "note",
                "updated_at",
            ]
        )
        add_interaction(
            agency,
            visit.agent,
            InteractionKind.VISIT,
            contact=visit.contact,
            listing=visit.listing,
            request=visit.request,
            summary=_("بازدید انجام شد — {}").format(visit.get_outcome_display()),
            detail=note,
            occurred_at=visit.completed_at,
        )
    return visit


def create_task(
    agency,
    user,
    *,
    title: str,
    assignee,
    due_at,
    description: str = "",
    priority: str | None = None,
    related_contact=None,
    related_listing=None,
    related_request=None,
    commit: bool = True,
):
    """Create a Task assigned to *assignee* with an optional related object."""
    from apps.crm.models import Task, TaskPriority

    task = Task(
        agency=agency,
        title=title,
        description=description,
        assignee=assignee,
        due_at=due_at,
        priority=priority or TaskPriority.NORMAL,
        related_contact=related_contact,
        related_listing=related_listing,
        related_request=related_request,
    )
    if commit:
        task.save()
    return task


def complete_task(task, *, cancelled: bool = False):
    """Mark a Task done (or cancelled)."""
    from apps.crm.models import TaskStatus

    task.status = TaskStatus.CANCELLED if cancelled else TaskStatus.DONE
    task.completed_at = timezone.now()
    task.save(update_fields=["status", "completed_at", "updated_at"])
    return task


def notify(user, *, kind: str = "info", title: str, body: str = "", link: str = ""):
    """Create an in-app Notification for *user* (agency taken from user's membership)."""
    from apps.crm.models import Notification

    agency = getattr(user, "agency", None)
    if agency is None:
        membership = user.agency_memberships.first()
        agency = membership.agency if membership else None

    return Notification.objects.create(
        agency=agency,
        user=user,
        kind=kind,
        title=title,
        body=body,
        link=link,
    )
