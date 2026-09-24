"""
AI service layer — Phase 5A + 5B.

Public API:
- create_voice_note(agency, uploaded_file, ...)
    Validates audio (size + magic bytes) and creates a VoiceNote in UPLOADED state.

- enqueue_transcription(voice_note)
    Moves the note to QUEUED and fires the Celery transcription task.

- run_transcription(voice_note_id)
    Called by the Celery task; calls the provider and stores the transcript.

- get_transcription_provider_for_agency(agency)
    Returns the active adapter, falling back to ConsoleTranscriptionProvider.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.ai.models import (
    AIProvider,
    ALLOWED_AUDIO_MIMES,
    MAX_AUDIO_SIZE_BYTES,
    AgencyAIConfig,
    VoiceNote,
    VoiceNoteState,
)

if TYPE_CHECKING:
    from django.core.files import File

    from apps.agencies.models import Agency
    from apps.accounts.models import CustomUser
    from apps.listings.models import Listing

logger = logging.getLogger(__name__)


# ─── MIME sniffing ────────────────────────────────────────────────────────────

_MAGIC_AUDIO = [
    (b"OggS", "audio/ogg"),
    (b"\x1a\x45\xdf\xa3", "audio/webm"),  # Matroska/WebM container
    (b"fLaC", "audio/flac"),
    (b"ID3", "audio/mpeg"),
]


def detect_audio_mime(data: bytes) -> str:
    """
    Detect an audio MIME from the first bytes of the file.

    Returns a best-guess MIME or "" when the content is not recognisable.
    """
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return "audio/mp4"  # m4a / mp4 recordings
    for magic, mime in _MAGIC_AUDIO:
        if data[: len(magic)] == magic:
            return mime
    if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return "audio/mpeg"  # bare MPEG audio frame
    return ""


# ─── Provider resolution ──────────────────────────────────────────────────────


def get_ai_config_for_agency(agency: Agency) -> AgencyAIConfig | None:
    """Return the active AI config for the agency, or None."""
    return AgencyAIConfig.objects.filter(agency=agency, is_active=True).first()


def get_transcription_provider_for_agency(agency: Agency):
    """Return the TranscriptionProvider adapter for the agency.

    Falls back to ConsoleTranscriptionProvider when no active config exists.
    """
    from apps.ai.providers.console import ConsoleTranscriptionProvider
    from apps.ai.providers.gemini import GeminiTranscriptionProvider
    from apps.ai.providers.openai_whisper import OpenAITranscriptionProvider

    config = get_ai_config_for_agency(agency)
    if config is None:
        return ConsoleTranscriptionProvider()
    if config.provider == AIProvider.OPENAI:
        return OpenAITranscriptionProvider(
            api_key=config.api_key or "",
            model=config.model_name or "whisper-1",
        )
    if config.provider == AIProvider.GEMINI:
        return GeminiTranscriptionProvider(
            api_key=config.api_key or "",
            model=config.model_name or "gemini-2.0-flash",
        )
    return ConsoleTranscriptionProvider()


# ─── Create (upload) ──────────────────────────────────────────────────────────


def create_voice_note(
    agency: Agency,
    uploaded_file: File,
    listing: Listing | None = None,
    uploaded_by: CustomUser | None = None,
    language: str = "fa",
) -> VoiceNote:
    """
    Validate and store an uploaded audio file as a VoiceNote.

    Raises ValidationError when the file is missing, too large, or the
    content is not a recognisable audio container.
    """
    data = uploaded_file.read(MAX_AUDIO_SIZE_BYTES + 1)
    uploaded_file.seek(0)

    if not data:
        raise ValidationError("فایل صوتی خالی است.")
    if len(data) > MAX_AUDIO_SIZE_BYTES:
        raise ValidationError("حجم فایل صوتی بیش از حد مجاز است (حداکثر ۲۰ مگابایت).")

    mime = detect_audio_mime(data)
    if not mime or mime not in ALLOWED_AUDIO_MIMES:
        raise ValidationError("فرمت فایل صوتی پشتیبانی نمی‌شود.")

    note = VoiceNote.objects.create(
        agency=agency,
        listing=listing,
        audio=uploaded_file,
        original_filename=uploaded_file.name[:300],
        mime_type=mime,
        file_size=len(data),
        language=language,
        uploaded_by=uploaded_by,
    )
    logger.info("VoiceNote #%d created (%d bytes, %s)", note.pk, len(data), mime)
    return note


# ─── Enqueue ──────────────────────────────────────────────────────────────────


def enqueue_transcription(voice_note: VoiceNote) -> VoiceNote:
    """
    Queue a VoiceNote for transcription and dispatch the Celery task.

    The actual provider call happens inside the task (constitution §5).
    """
    from apps.ai.tasks import transcribe_voice_task

    if voice_note.status not in (VoiceNoteState.UPLOADED, VoiceNoteState.FAILED):
        return voice_note  # already queued/in-flight/done — idempotent guard

    config = get_ai_config_for_agency(voice_note.agency)
    voice_note.status = VoiceNoteState.QUEUED
    voice_note.provider = config.provider if config else AIProvider.CONSOLE
    voice_note.error_message = ""
    voice_note.save(update_fields=["status", "provider", "error_message", "updated_at"])
    transcribe_voice_task.delay(voice_note.pk)
    return voice_note


# ─── Transcribe (called by Celery task) ───────────────────────────────────────


def run_transcription(voice_note_id: int) -> None:
    """
    Perform the provider call and store the transcript.

    State machine: queued/failed → transcribing → transcribed (or failed).
    Raises on error so the Celery task can retry with backoff.
    """
    voice_note = VoiceNote.all_objects.select_related("agency").get(pk=voice_note_id)

    if voice_note.status in (VoiceNoteState.TRANSCRIBED,):
        return  # idempotent guard

    voice_note.status = VoiceNoteState.TRANSCRIBING
    voice_note.save(update_fields=["status", "updated_at"])

    try:
        provider = get_transcription_provider_for_agency(voice_note.agency)
        result = provider.transcribe(voice_note.audio.path, voice_note.language)
        voice_note.transcript = result.text
        voice_note.duration_seconds = (
            int(result.duration_seconds)
            if result.duration_seconds
            else voice_note.duration_seconds
        )
        voice_note.provider_file_id = result.provider_file_id[:200]
        voice_note.status = VoiceNoteState.TRANSCRIBED
        voice_note.transcribed_at = timezone.now()
        voice_note.save(
            update_fields=[
                "transcript",
                "duration_seconds",
                "provider_file_id",
                "status",
                "transcribed_at",
                "updated_at",
            ]
        )
        logger.info("VoiceNote #%d transcribed via %s", voice_note_id, result.provider)
    except Exception as exc:
        voice_note.status = VoiceNoteState.FAILED
        voice_note.error_message = str(exc)[:500]
        voice_note.save(update_fields=["status", "error_message", "updated_at"])
        logger.error("VoiceNote #%d transcription failed: %s", voice_note_id, exc)
        raise
