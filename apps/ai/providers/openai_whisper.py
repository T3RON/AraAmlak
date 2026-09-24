"""
OpenAI Whisper transcription adapter.

Official docs (read 2026-09): https://developers.openai.com — Audio →
Create a transcription.

Endpoint:
  POST https://api.openai.com/v1/audio/transcriptions   (multipart/form-data)

Parameters:
  file            — audio file (mp3, mp4, mpeg, mpga, m4a, wav, webm); max 25 MB
  model           — "whisper-1" (or gpt-4o-transcribe family)
  language        — optional ISO-639-1 code, e.g. "fa"
  response_format — "json" (default) → {"text": "..."}

Errors: non-2xx → raise_for_status; JSON body carries {"error": {...}}.
"""

from __future__ import annotations

import logging
from pathlib import Path

import requests

from .base import TranscriptionProvider, TranscriptionResult

logger = logging.getLogger(__name__)

_URL = "https://api.openai.com/v1/audio/transcriptions"
_TIMEOUT = 120  # seconds — long audio needs more than the usual 10s


class OpenAITranscriptionProvider(TranscriptionProvider):
    """
    Adapter for OpenAI speech-to-text (Whisper family).

    Parameters
    ----------
    api_key : str — OpenAI API key (stored encrypted in AgencyAIConfig)
    model   : str — model name, default "whisper-1"
    """

    def __init__(self, api_key: str, model: str = "whisper-1") -> None:
        self._api_key = api_key
        self._model = model

    def transcribe(self, audio_path: str, language: str = "fa") -> TranscriptionResult:
        audio_file = Path(audio_path)
        with audio_file.open("rb") as fh:
            resp = requests.post(
                _URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                files={"file": (audio_file.name, fh)},
                data={
                    "model": self._model,
                    "language": language,
                    "response_format": "json",
                },
                timeout=_TIMEOUT,
            )
        resp.raise_for_status()
        data = resp.json()
        text = (data.get("text") or "").strip()
        if not text:
            raise RuntimeError("OpenAI transcription returned empty text")
        logger.info("[OpenAI] transcribed %s (%d chars)", audio_file.name, len(text))
        return TranscriptionResult(
            text=text,
            provider="openai",
            language=language,
            raw=data,
        )
