"""
AI app models — Phase 5A + 5B.

Models:
- AgencyAIConfig : per-agency AI provider config (encrypted API key)
- VoiceNote      : uploaded audio with transcription state machine
- VoiceDraft     : structured listing draft extracted from a transcript

VoiceNote state machine:
  uploaded → queued → transcribing → transcribed
                          ↘ failed
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import EncryptedCharField
from apps.core.models import AgencyOwned, TimeStampedModel

# ─── Choices ──────────────────────────────────────────────────────────────────


class AIProvider(models.TextChoices):
    OPENAI = "openai", _("OpenAI (Whisper)")
    GEMINI = "gemini", _("گوگل Gemini")
    CONSOLE = "console", _("کنسول (توسعه)")


class VoiceNoteState(models.TextChoices):
    UPLOADED = "uploaded", _("آپلودشده")
    QUEUED = "queued", _("صف رونویسی")
    TRANSCRIBING = "transcribing", _("در حال رونویسی")
    TRANSCRIBED = "transcribed", _("رونویسی‌شده")
    FAILED = "failed", _("ناموفق")


class DraftState(models.TextChoices):
    DRAFT = "draft", _("پیش‌نویس")
    APPLIED = "applied", _("به فایل اعمال‌شده")


# 20MB — within both OpenAI (25MB file) and Gemini inline (20MB total request) limits
MAX_AUDIO_SIZE_BYTES = 20 * 1024 * 1024

ALLOWED_AUDIO_MIMES = [
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/m4a",
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
    "audio/webm",
    "audio/flac",
]


def _voice_upload_path(instance: VoiceNote, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return f"ai/voice/{instance.agency_id}/{uuid4().hex}{ext}"


# ─── AgencyAIConfig ───────────────────────────────────────────────────────────


class AgencyAIConfig(AgencyOwned, TimeStampedModel):
    """
    Per-agency AI provider configuration.

    API keys are encrypted at rest. When no active config exists the
    ConsoleTranscriptionProvider is used as a dev/test fallback.
    """

    provider = models.CharField(
        _("ارائه‌دهنده"),
        max_length=20,
        choices=AIProvider.choices,
        default=AIProvider.CONSOLE,
    )
    api_key = EncryptedCharField(
        _("کلید API"),
        blank=True,
        help_text=_("رمزنگاری‌شده در پایگاه داده"),
    )
    model_name = models.CharField(
        _("نام مدل"),
        max_length=100,
        blank=True,
        help_text=_("مثلاً whisper-1 یا gemini-2.0-flash — خالی = پیش‌فرض ارائه‌دهنده"),
    )
    is_active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("تنظیمات هوش مصنوعی آژانس")
        verbose_name_plural = _("تنظیمات هوش مصنوعی آژانس‌ها")

    def __str__(self) -> str:
        return f"{self.agency} — {self.get_provider_display()}"


# ─── VoiceNote ────────────────────────────────────────────────────────────────


class VoiceNote(AgencyOwned, TimeStampedModel):
    """
    A recorded/uploaded audio note describing a property.

    The transcript is filled by the Celery transcription task. Audio files
    are stored under MEDIA_ROOT/ai/voice/<agency_id>/ with random names.
    """

    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="voice_notes",
        verbose_name=_("فایل ملک"),
    )
    audio = models.FileField(
        _("فایل صوتی"),
        upload_to=_voice_upload_path,
        max_length=500,
    )
    original_filename = models.CharField(
        _("نام فایل اصلی"), max_length=300, blank=True
    )
    mime_type = models.CharField(_("نوع MIME"), max_length=100, blank=True)
    file_size = models.PositiveBigIntegerField(_("حجم (بایت)"), default=0)
    duration_seconds = models.PositiveIntegerField(
        _("مدت (ثانیه)"), null=True, blank=True
    )
    language = models.CharField(_("زبان"), max_length=10, default="fa")
    status = models.CharField(
        _("وضعیت"),
        max_length=20,
        choices=VoiceNoteState.choices,
        default=VoiceNoteState.UPLOADED,
        db_index=True,
    )
    transcript = models.TextField(_("متن رونویسی"), blank=True)
    provider = models.CharField(
        _("ارائه‌دهنده"),
        max_length=20,
        choices=AIProvider.choices,
        blank=True,
    )
    provider_file_id = models.CharField(
        _("شناسه نزد ارائه‌دهنده"), max_length=200, blank=True
    )
    error_message = models.CharField(_("پیغام خطا"), max_length=500, blank=True)
    transcribed_at = models.DateTimeField(_("زمان رونویسی"), null=True, blank=True)
    uploaded_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_voice_notes",
        verbose_name=_("آپلود توسط"),
    )

    class Meta:
        verbose_name = _("یادداشت صوتی")
        verbose_name_plural = _("یادداشت‌های صوتی")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "status"]),
            models.Index(fields=["agency", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Voice #{self.pk} [{self.status}] {self.original_filename[:40]}"

    @property
    def is_terminal(self) -> bool:
        """True when the transcription workflow has finished (either way)."""
        return self.status in (
            VoiceNoteState.TRANSCRIBED,
            VoiceNoteState.FAILED,
        )


# ─── VoiceDraft ───────────────────────────────────────────────────────────────


class VoiceDraft(AgencyOwned, TimeStampedModel):
    """
    Structured listing draft extracted from a VoiceNote transcript.

    `data` maps Listing field names to parsed values (Persian prices are
    already converted to integer Tomans). `missing` lists required fields
    that could not be found in the transcript.
    """

    voice_note = models.OneToOneField(
        VoiceNote,
        on_delete=models.CASCADE,
        related_name="draft",
        verbose_name=_("یادداشت صوتی"),
    )
    data = models.JSONField(_("داده استخراج‌شده"), default=dict)
    missing = models.JSONField(_("فیلدهای ناموجود"), default=list)
    confidence = models.FloatField(_("اطمینان"), default=0.0)
    parser = models.CharField(_("پارسر"), max_length=20, blank=True)
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="voice_drafts",
        verbose_name=_("فایل ساخته‌شده"),
    )
    status = models.CharField(
        _("وضعیت"),
        max_length=20,
        choices=DraftState.choices,
        default=DraftState.DRAFT,
        db_index=True,
    )

    class Meta:
        verbose_name = _("پیش‌نویس صوتی")
        verbose_name_plural = _("پیش‌نویس‌های صوتی")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"VoiceDraft #{self.pk} [{self.status}] voice={self.voice_note_id}"
