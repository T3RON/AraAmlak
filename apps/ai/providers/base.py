"""
TranscriptionProvider — abstract interface all speech-to-text adapters implement.

Design (mirrors apps/messaging/providers):
- transcribe() → TranscriptionResult(text, language, duration_seconds, provider)
- Adapters never raise provider-specific exceptions upward as strings;
  they raise on failure so the Celery task can retry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TranscriptionResult:
    """Result of a transcription call."""

    text: str
    provider: str
    language: str = "fa"
    duration_seconds: float | None = None
    provider_file_id: str = ""
    raw: dict = field(default_factory=dict)


class TranscriptionProvider(ABC):
    """Abstract base for all speech-to-text provider adapters."""

    @abstractmethod
    def transcribe(self, audio_path: str, language: str = "fa") -> TranscriptionResult:
        """
        Transcribe the audio file at `audio_path` (filesystem path).

        Parameters
        ----------
        audio_path : path to the audio file on local storage
        language   : ISO-639-1 hint (e.g. "fa")

        Returns
        -------
        TranscriptionResult

        Raises
        ------
        Exception on network/provider failure — the caller (Celery task)
        decides on retry policy.
        """
