"""
CRM app models: Request (درخواست / نیازمندی مراجعه‌کننده).

Every Request is tenant-scoped via AgencyOwned.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import EncryptedCharField
from apps.core.models import AgencyOwned
from apps.listings.models import DealType  # reuse choice enums

# ─── Choices ──────────────────────────────────────────────────────────────────


class RequestSource(models.TextChoices):
    WALK_IN = "walk_in", _("مراجعه حضوری")
    REFERRAL = "referral", _("معرفی")
    PORTAL = "portal", _("پورتال")
    SOCIAL = "social", _("شبکه اجتماعی")
    DIRECT = "direct", _("تماس مستقیم")
    OTHER = "other", _("سایر")


class RequestStatus(models.TextChoices):
    NEW = "new", _("جدید")
    IN_PROGRESS = "in_progress", _("در حال پیگیری")
    MATCHED = "matched", _("تطبیق یافته")
    CLOSED = "closed", _("بسته شده")
    CANCELLED = "cancelled", _("لغو شده")


class RequestPriority(models.TextChoices):
    LOW = "low", _("کم")
    NORMAL = "normal", _("معمولی")
    HIGH = "high", _("بالا")
    URGENT = "urgent", _("فوری")


# ─── Request (درخواست) ────────────────────────────────────────────────────────


class Request(AgencyOwned):
    """
    A buyer/renter need registered by an agent on behalf of a client (مراجعه‌کننده).

    client_phone is encrypted at rest.
    property_types is stored as JSON list of PropertyType values.
    Budget is in Tomans (BigIntegerField).
    """

    # --- Client info ---
    client_name = models.CharField(_("نام مراجعه‌کننده"), max_length=200)
    client_phone = EncryptedCharField(
        _("شماره مراجعه‌کننده"), max_length=255, blank=True
    )
    source = models.CharField(
        _("منبع مراجعه"),
        max_length=20,
        choices=RequestSource.choices,
        default=RequestSource.WALK_IN,
    )

    # --- Need specification ---
    deal_type = models.CharField(
        _("نوع معامله"),
        max_length=20,
        choices=DealType.choices,
        default=DealType.SALE,
        db_index=True,
    )
    # JSON list of PropertyType values, e.g. ["apartment", "villa"]
    property_types = models.JSONField(
        _("نوع ملک موردنظر"),
        default=list,
        blank=True,
    )
    min_area = models.PositiveIntegerField(_("حداقل متراژ"), null=True, blank=True)
    max_area = models.PositiveIntegerField(_("حداکثر متراژ"), null=True, blank=True)
    min_rooms = models.PositiveSmallIntegerField(
        _("حداقل اتاق"), null=True, blank=True
    )
    max_rooms = models.PositiveSmallIntegerField(
        _("حداکثر اتاق"), null=True, blank=True
    )
    city = models.CharField(_("شهر"), max_length=100, blank=True, db_index=True)
    district = models.CharField(_("منطقه / محله"), max_length=200, blank=True)
    min_budget = models.BigIntegerField(
        _("حداقل بودجه (تومان)"), null=True, blank=True
    )
    max_budget = models.BigIntegerField(
        _("حداکثر بودجه (تومان)"), null=True, blank=True
    )
    notes = models.TextField(_("توضیحات"), blank=True)

    # --- Workflow ---
    status = models.CharField(
        _("وضعیت"),
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.NEW,
        db_index=True,
    )
    priority = models.CharField(
        _("اولویت"),
        max_length=10,
        choices=RequestPriority.choices,
        default=RequestPriority.NORMAL,
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_requests",
        verbose_name=_("مشاور مسئول"),
    )

    # --- Dates ---
    contacted_at = models.DateTimeField(_("آخرین تماس"), null=True, blank=True)
    closed_at = models.DateTimeField(_("تاریخ بستن"), null=True, blank=True)

    class Meta:
        verbose_name = _("درخواست")
        verbose_name_plural = _("درخواست‌ها")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "status"]),
            models.Index(fields=["agency", "deal_type"]),
            models.Index(fields=["agency", "priority", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.client_name} — {self.get_deal_type_display()} ({self.get_status_display()})"
