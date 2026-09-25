"""
Regex-based Persian draft provider — offline fallback (Phase 5B parser).
"""

from __future__ import annotations

from .draft_base import DraftProvider


class RegexPersianDraftProvider(DraftProvider):
    """Wraps the deterministic Persian regex parser (no external calls)."""

    name = "regex_fa"
    is_async = False

    def extract(self, transcript: str) -> dict:
        from apps.ai.draft_parser import parse_listing_transcript

        return parse_listing_transcript(transcript)
