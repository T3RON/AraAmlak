"""
Publishing app models: PortalConfig and PublishJob.

PortalConfig: per-agency credentials/settings for a portal.
PublishJob: a single publish attempt for a Listing to a portal.

Both are tenant-scoped via AgencyOwned.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import EncryptedCharField
from apps.core.models import AgencyOwned

# ─── Choices ──────────────────────────────────────────────────────────────────


class Portal(models.TextChoices):
    DUMMY = "dummy", _("پورتال آزمایشی (Dummy)")
    DIVAR = "divar", _("دیوار")
    SHEYPOOR = "sheypoor", _("شیپور")


class JobStatus(models.TextChoices):
    PENDING = "pending", _("در انتظار")
    RUNNING = "running", _("در حال ارسال")
    SUCCESS = "success", _("موفق")
    FAILED = "failed", _("ناموفق")


# ─── PortalConfig ──────────────────────────────────────────────────────────────


class PortalConfig(AgencyOwned):
    """
    Per-agency configuration for a portal (e.g. Divar, Sheypoor).

    `credentials` is encrypted at rest — stores API token / key.
    Only one active config per (agency, portal) pair is allowed.
    """

    portal = models.CharField(
        _("پورتال"),
        max_length=20,
        choices=Portal.choices,
        default=Portal.DUMMY,
        db_index=True,
    )
    is_active = models.BooleanField(_("فعال"), default=True, db_index=True)
    credentials = EncryptedCharField(
        _("اطلاعات دسترسی (API key / token)"),
        max_length=2000,
        blank=True,
    )
    extra_config = models.JSONField(
        _("تنظیمات اضافه"),
        default=dict,
        blank=True,
        help_text=_("تنظیمات اختصاصی هر پورتال به صورت JSON"),
    )

    class Meta:
        verbose_name = _("تنظیمات پورتال")
        verbose_name_plural = _("تنظیمات پورتال‌ها")
        ordering = ["portal", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["agency", "portal"],
                condition=models.Q(is_active=True),
                name="unique_active_portal_per_agency",
            )
        ]
        indexes = [
            models.Index(fields=["agency", "portal", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_portal_display()} — {self.agency}"


# ─── PublishJob ───────────────────────────────────────────────────────────────


class PublishJob(AgencyOwned):
    """
    A single publish-to-portal attempt for one Listing.

    `external_id` is the ID assigned by the portal after a successful publish.
    `error_message` stores the last error for failed jobs.
    `retries` tracks how many times Celery has retried.
    """

    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="publish_jobs",
        verbose_name=_("فایل ملک"),
    )
    portal_config = models.ForeignKey(
        PortalConfig,
        on_delete=models.CASCADE,
        related_name="jobs",
        verbose_name=_("تنظیمات پورتال"),
    )
    status = models.CharField(
        _("وضعیت"),
        max_length=10,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        db_index=True,
    )
    external_id = models.CharField(
        _("شناسه در پورتال"),
        max_length=200,
        blank=True,
        help_text=_("ID آگهی پس از انتشار موفق"),
    )
    error_message = models.TextField(_("پیام خطا"), blank=True)
    published_at = models.DateTimeField(_("تاریخ انتشار"), null=True, blank=True)
    retries = models.PositiveSmallIntegerField(_("تعداد تلاش مجدد"), default=0)

    class Meta:
        verbose_name = _("کار انتشار")
        verbose_name_plural = _("کارهای انتشار")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "status"]),
            models.Index(fields=["agency", "listing"]),
            models.Index(fields=["listing", "portal_config"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.listing} → {self.portal_config.get_portal_display()}"
            f" [{self.get_status_display()}]"
        )
