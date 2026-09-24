"""
Google Gemini transcription adapter.

Official docs (read 2026-09): https://ai.google.dev/gemini-api/docs/audio
and https://ai.google.dev/gemini-api/docs/interactions

Endpoint:
  POST https://generativelanguage.googleapis.com/v1beta/interactions

Headers:
  x-goog-api-key: <API key>
  Content-Type: application/json

Request:
  {
    "model": "gemini-2.0-flash",
    "input": [
      {"type": "text",  "text": "Generate a transcript of the speech."},
      {"type": "audio", "data": "<base64>", "mime_type": "audio/mp3"}
    ]
  }

Inline audio limit: 20 MB total request (larger files require the Files API —
not implemented here; the service layer caps uploads at 20 MB and the adapter
refuses audio that would exceed the inline budget after base64 expansion).

Response: interaction resource with the generated text at "output_text"
(defensive fallback walks the "output" steps for text parts).

Supported audio MIME types: audio/wav, audio/mp3, audio/mpeg, audio/aac,
audio/ogg, audio/flac, audio/m4a, audio/opus, audio/webm, ...
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

import requests

from .base import TranscriptionProvider, TranscriptionResult

logger = logging.getLogger(__name__)

_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
_TIMEOUT = 120  # seconds
# Gemini inline budget is 20MB for the whole request; base64 inflates by 4/3.
_MAX_B64_BYTES = 18 * 1024 * 1024

_PROMPT = (
    "این فایل صوتی توضیحات یک مشاور املاک درباره یک فایل ملکی به زبان فارسی است. "
    "فقط و فقط متن گفتار را دقیق رونویسی کن؛ هیچ توضیح یا متن اضافه‌ای ننویس."
)


class GeminiTranscriptionProvider(TranscriptionProvider):
    """
    Adapter for Google Gemini speech-to-text.

    Parameters
    ----------
    api_key : str — Gemini API key (stored encrypted in AgencyAIConfig)
    model   : str — model name, default "gemini-2.0-flash"
    """

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self._api_key = api_key
        self._model = model

    @staticmethod
    def _extract_text(data: dict) -> str:
        """Pull the transcript out of an interaction response."""
        text = data.get("output_text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        # Defensive: walk output steps for text parts
        for step in data.get("output") or []:
            for part in (step.get("content") or {}).get("parts") or []:
                if part.get("type") == "text" and part.get("text"):
                    return part["text"].strip()
        return ""

    def transcribe(self, audio_path: str, language: str = "fa") -> TranscriptionResult:
        audio_file = Path(audio_path)
        audio_bytes = audio_file.read_bytes()
        b64 = base64.b64encode(audio_bytes)
        if len(b64) > _MAX_B64_BYTES:
            raise RuntimeError(
                f"Audio too large for Gemini inline ({len(b64)} bytes base64 > "
                f"{_MAX_B64_BYTES}); use a shorter recording or the Files API"
            )

        mime = {
            ".mp3": "audio/mp3",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
            ".m4a": "audio/m4a",
            ".mp4": "audio/mp4",
            ".webm": "audio/webm",
        }.get(audio_file.suffix.lower(), "audio/mpeg")

        payload = {
            "model": self._model,
            "input": [
                {"type": "text", "text": _PROMPT},
                {"type": "audio", "data": b64.decode("ascii"), "mime_type": mime},
            ],
        }
        resp = requests.post(
            _URL,
            headers={
                "x-goog-api-key": self._api_key,
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        text = self._extract_text(data)
        if not text:
            raise RuntimeError("Gemini transcription returned no text")
        logger.info("[Gemini] transcribed %s (%d chars)", audio_file.name, len(text))
        return TranscriptionResult(
            text=text,
            provider="gemini",
            language=language,
            raw=data,
        )
