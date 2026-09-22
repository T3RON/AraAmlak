"""
Core abstract base models and AuditLog.

Every tenant-scoped model inherits AgencyOwned.
Every model inherits TimeStampedModel for audit timestamps.
AuditLog records who changed what, when, from where.
"""

import threading

from django.conf import settings
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


# ─── AuditLog ─────────────────────────────────────────────────────────────────


class AuditAction(models.TextChoices):
    CREATE = "create", _("ایجاد")
    UPDATE = "update", _("ویرایش")
    DELETE = "delete", _("حذف")
    VIEW_PHONE = "view_phone", _("نمایش شماره")
    LOGIN = "login", _("ورود")
    LOGOUT = "logout", _("خروج")
    INVITE = "invite", _("دعوت عضو")
    PUBLISH = "publish", _("انتشار")
    OTHER = "other", _("سایر")


class AuditLog(models.Model):
    """
    Immutable audit trail.

    Records every significant action: who, what model/object, what action,
    when, from which IP, and an optional diff snapshot.

    Never update or delete AuditLog rows — append-only.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("کاربر"),
    )
    agency = models.ForeignKey(
        "agencies.Agency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("آژانس"),
        db_index=True,
    )
    action = models.CharField(
        _("اقدام"),
        max_length=20,
        choices=AuditAction.choices,
        default=AuditAction.OTHER,
        db_index=True,
    )
    # The model name and pk of the affected object (nullable for session actions)
    object_model = models.CharField(_("مدل"), max_length=100, blank=True, db_index=True)
    object_id = models.CharField(_("شناسه شیء"), max_length=50, blank=True, db_index=True)
    object_repr = models.CharField(_("نمایش شیء"), max_length=300, blank=True)
    # Optional JSON diff: {"field": [old_value, new_value], ...}
    diff = models.JSONField(_("تغییرات"), null=True, blank=True)
    ip_address = models.GenericIPAddressField(_("آدرس IP"), null=True, blank=True)
    user_agent = models.CharField(_("مرورگر"), max_length=300, blank=True)
    extra = models.JSONField(_("اطلاعات اضافه"), null=True, blank=True)
    created_at = models.DateTimeField(_("زمان"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("لاگ ممیزی")
        verbose_name_plural = _("لاگ‌های ممیزی")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "action", "-created_at"]),
            models.Index(fields=["actor", "-created_at"]),
            models.Index(fields=["object_model", "object_id"]),
        ]

    def __str__(self) -> str:
        actor_str = str(self.actor) if self.actor_id else "سیستم"
        obj_label = self.object_repr or self.object_model
        return f"{actor_str} | {self.get_action_display()} | {obj_label}"

    @classmethod
    def log(
        cls,
        *,
        actor=None,
        agency=None,
        action: str,
        obj=None,
        diff: dict | None = None,
        request=None,
        extra: dict | None = None,
    ) -> "AuditLog":
        """
        Convenience factory. Usage:
            AuditLog.log(actor=request.user, agency=agency, action=AuditAction.UPDATE,
                         obj=listing, diff={"status": ["active", "sold"]}, request=request)
        """
        ip = None
        ua = ""
        if request is not None:
            x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
            ip = (
                x_forwarded.split(",")[0].strip()
                if x_forwarded
                else request.META.get("REMOTE_ADDR")
            )
            ua = request.META.get("HTTP_USER_AGENT", "")[:300]

        obj_model = ""
        obj_id = ""
        obj_repr = ""
        if obj is not None:
            obj_model = obj.__class__.__name__
            obj_id = str(getattr(obj, "pk", ""))
            obj_repr = str(obj)[:300]

        return cls.objects.create(
            actor=actor,
            agency=agency,
            action=action,
            object_model=obj_model,
            object_id=obj_id,
            object_repr=obj_repr,
            diff=diff,
            ip_address=ip,
            user_agent=ua,
            extra=extra,
        )
