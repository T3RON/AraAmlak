"""
Console / Fake transcription adapter — for development and testing.

Behaviour:
- transcribe(): returns a deterministic canned Persian transcript describing
  a sample apartment; never calls the network.
- Set AgencyAIConfig.provider = "console" (or leave no config) in dev.
"""

from __future__ import annotations

import logging

from .base import TranscriptionProvider, TranscriptionResult

logger = logging.getLogger(__name__)

_counter = 0

CANNED_TRANSCRIPT = (
    "یک آپارتمان فروشی در محله سعادت‌آباد، هشتاد متر، دو خواب، "
    "طبقه سوم از پنج طبقه، ساخت ۱۳۹۰، شمالی، پارکینگ دارد، آسانسور دارد، "
    "انباری دارد، قیمت پنج میلیارد تومان."
)


def _next_id() -> str:
    global _counter
    _counter += 1
    return f"FAKE-TR-{_counter:06d}"


class ConsoleTranscriptionProvider(TranscriptionProvider):
    """
    Fake transcriber: logs the request and returns a canned Persian
    transcript. Never performs network I/O — safe for tests and local dev.
    """

    def transcribe(self, audio_path: str, language: str = "fa") -> TranscriptionResult:
        file_id = _next_id()
        logger.info("[AI-CONSOLE] transcribe path=%s lang=%s id=%s", audio_path, language, file_id)
        return TranscriptionResult(
            text=CANNED_TRANSCRIPT,
            provider="console",
            language=language,
            duration_seconds=42,
            provider_file_id=file_id,
        )
