"""
Celery tasks for the AI app.

Tasks:
- transcribe_voice_task: transcribe a VoiceNote with retry and exponential backoff.
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)

_MAX_RETRIES = 5
_BACKOFF_BASE = 60  # seconds — doubles each retry: 60, 120, 240, 480, 960


@shared_task(
    bind=True,
    max_retries=_MAX_RETRIES,
    acks_late=True,
    name="apps.ai.tasks.transcribe_voice_task",
)
def transcribe_voice_task(self, voice_note_id: int) -> None:
    """
    Transcribe a queued VoiceNote via the agency's provider.

    Retries up to _MAX_RETRIES times with exponential backoff on any error.
    """
    from apps.ai.services import run_transcription

    try:
        run_transcription(voice_note_id)
    except Exception as exc:
        countdown = _BACKOFF_BASE * (2 ** self.request.retries)
        logger.warning(
            "transcribe_voice_task: VoiceNote #%d attempt %d failed — retry in %ds: %s",
            voice_note_id,
            self.request.retries + 1,
            countdown,
            exc,
        )
        raise self.retry(exc=exc, countdown=countdown) from exc
