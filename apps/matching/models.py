"""
Matching app models: Match (تطبیق فایل با درخواست).

Every Match is tenant-scoped (agency FK).
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AgencyManager, TimeStampedModel, UnfilteredAgencyManager


class Match(TimeStampedModel):
    """
    A scored match between a Listing (فایل) and a Request (درخواست).

    Scoring is done by matching/services.py and stored here for fast retrieval.
    agency is denormalized from request for efficient tenant filtering.
    """

    agency = models.ForeignKey(
        "agencies.Agency",
        on_delete=models.CASCADE,
        related_name="matches",
        verbose_name=_("آژانس"),
        db_index=True,
    )
    request = models.ForeignKey(
        "crm.Request",
        on_delete=models.CASCADE,
        related_name="matches",
        verbose_name=_("درخواست"),
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="matches",
        verbose_name=_("فایل ملک"),
    )
    score = models.PositiveSmallIntegerField(
        _("امتیاز تطبیق"),
        default=0,
        help_text=_("۰ تا ۱۰۰ — هر چه بالاتر، تطبیق بهتر"),
    )

    objects = AgencyManager()
    all_objects = UnfilteredAgencyManager()

    class Meta:
        verbose_name = _("تطبیق")
        verbose_name_plural = _("تطبیق‌ها")
        unique_together = [("request", "listing")]
        ordering = ["-score", "-created_at"]
        indexes = [
            models.Index(fields=["agency", "score"]),
            models.Index(fields=["request", "score"]),
        ]

    def __str__(self) -> str:
        return (
            f"Match #{self.pk}: درخواست {self.request_id}"
            f" ↔ فایل {self.listing_id} [{self.score}]"
        )
