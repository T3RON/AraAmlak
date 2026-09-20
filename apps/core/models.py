"""
Core abstract base models.

Every tenant-scoped model inherits AgencyOwned.
Every model inherits TimeStampedModel for audit timestamps.
"""

import threading

from django.db import models
from django.utils.translation import gettext_lazy as _

# ─── Thread-local store for current agency context ────────────────────────────
_thread_local = threading.local()


def get_current_agency():
    """Return the Agency instance bound to the current request thread (or None)."""
    return getattr(_thread_local, "current_agency", None)


def set_current_agency(agency):
    """Bind an agency to the current thread (called from middleware)."""
    _thread_local.current_agency = agency


def clear_current_agency():
    """Clear the thread-local agency (called at end of request)."""
    _thread_local.current_agency = None


# ─── Managers ─────────────────────────────────────────────────────────────────


class AgencyManager(models.Manager):
    """
    Default manager that filters queryset by the thread-local current agency.

    When no agency is set in thread-local (e.g. superadmin context),
    the full queryset is returned.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        agency = get_current_agency()
        if agency is not None:
            return qs.filter(agency=agency)
        return qs


class UnfilteredAgencyManager(models.Manager):
    """Manager that always returns all rows regardless of tenant context."""

    pass


# ─── Abstract Base Models ─────────────────────────────────────────────────────


class TimeStampedModel(models.Model):
    """Abstract model with created_at and updated_at."""

    created_at = models.DateTimeField(_("تاریخ ایجاد"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاریخ به‌روزرسانی"), auto_now=True)

    class Meta:
        abstract = True


class AgencyOwned(TimeStampedModel):
    """
    Abstract model for all tenant-scoped records.

    - `agency` is mandatory (non-nullable).
    - Default manager filters by thread-local agency.
    - `all_objects` manager bypasses tenant filter (for admin/superadmin use).
    """

    agency = models.ForeignKey(
        "agencies.Agency",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
        verbose_name=_("آژانس"),
        db_index=True,
    )

    objects = AgencyManager()
    all_objects = UnfilteredAgencyManager()

    class Meta:
        abstract = True
