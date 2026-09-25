"""
DraftProvider — abstract interface for transcript → listing-draft extraction.

Implementations:
- RegexPersianDraftProvider : deterministic Persian regex parser (offline)
- GeminiDraftProvider       : Gemini structured output (external → async)
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class DraftProvider(ABC):
    """Abstract base for all draft-extraction providers."""

    #: Stable identifier stored in VoiceDraft.parser
    name: str = "base"

    #: True when extract() performs an external call — must run in Celery.
    is_async: bool = False

    @abstractmethod
    def extract(self, transcript: str) -> dict:
        """
        Parse a Persian transcript into structured listing fields.

        Returns
        -------
        {
            "data":       {field: value, ...},
            "missing":    [field, ...],
            "confidence": float (0..1),
        }

        Raises on provider failure (network/parse) — callers decide retry.
        """
