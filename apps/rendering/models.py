"""
Rendering app models — Phase 6A.

Models:
- RenderJob : poster render pipeline for a Listing (PDF / PNG)

State machine (mirrors publishing.PublishJob):
  pending → running → success
                  ↘ failed
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AgencyOwned, TimeStampedModel

# ─── Choices ──────────────────────────────────────────────────────────────────


class RenderKind(models.TextChoices):
    POSTER_PDF = "poster_pdf", _("پوستر PDF")
    POSTER_PNG = "poster_png", _("پوستر PNG")


class RenderStatus(models.TextChoices):
    PENDING = "pending", _("صف")
    RUNNING = "running", _("در حال رندر")
    SUCCESS = "success", _("موفق")
    FAILED = "failed", _("ناموفق")


def _render_output_path(instance: "RenderJob", filename: str) -> str:
    ext = Path(filename).suffix.lower() or ".pdf"
    return f"rendering/{instance.agency_id}/{uuid4().hex}{ext}"


# ─── RenderJob ────────────────────────────────────────────────────────────────


class RenderJob(AgencyOwned):
    """One poster render attempt for a listing."""

    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="render_jobs",
        verbose_name=_("فایل ملک"),
    )
    kind = models.CharField(
        _("نوع خروجی"),
        max_length=20,
        choices=RenderKind.choices,
        default=RenderKind.POSTER_PDF,
    )
    status = models.CharField(
        _("وضعیت"),
        max_length=20,
        choices=RenderStatus.choices,
        default=RenderStatus.PENDING,
        db_index=True,
    )
    engine = models.CharField(_("موتور رندر"), max_length=30, blank=True)
    file = models.FileField(
        _("فایل خروجی"),
        upload_to=_render_output_path,
        max_length=500,
        blank=True,
    )
    error_message = models.CharField(_("پیغام خطا"), max_length=500, blank=True)
    rendered_at = models.DateTimeField(_("زمان رندر"), null=True, blank=True)

    class Meta:
        verbose_name = _("job رندر")
        verbose_name_plural = _("jobهای رندر")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "status"]),
            models.Index(fields=["listing", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Render #{self.pk} {self.listing} [{self.status}]"
