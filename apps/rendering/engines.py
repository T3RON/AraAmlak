"""
Render engines — Phase 6A.

`BaseRenderEngine` ABC with two implementations:
- PlaywrightRenderEngine : real HTML → PDF/PNG via headless Chromium
                           (constitution §1: PDF/PNG render = Playwright)
- StubRenderEngine       : dev/test fallback producing minimal valid bytes
                           when no browser is available

Selection: settings.RENDER_BACKEND = "playwright" (default) | "stub".
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from django.conf import settings

logger = logging.getLogger(__name__)

# Minimal-but-valid output bytes for the stub engine
_STUB_PDF = b"%PDF-1.4\n% ara-amlak stub render (no browser)\n"
_STUB_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class BaseRenderEngine(ABC):
    """Abstract base for all render engines."""

    name: str = "base"

    @abstractmethod
    def render(self, html: str, kind: str = "poster_pdf") -> bytes:
        """Render the given self-contained HTML and return file bytes."""


class PlaywrightRenderEngine(BaseRenderEngine):
    """HTML → PDF/PNG with headless Chromium (Playwright)."""

    name = "playwright"

    def render(self, html: str, kind: str = "poster_pdf") -> bytes:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.set_content(html, wait_until="load")
                if kind == "poster_png":
                    return page.screenshot(full_page=True, type="png")
                return page.pdf(format="A4", print_background=True)
            finally:
                browser.close()


class StubRenderEngine(BaseRenderEngine):
    """
    Returns minimal valid bytes without a browser.

    Never use in production output paths — exists so the pipeline (state
    machine, storage, views) works in environments without Chromium.
    """

    name = "stub"

    def render(self, html: str, kind: str = "poster_pdf") -> bytes:
        logger.info("[RENDER-STUB] kind=%s len=%d", kind, len(html))
        if kind == "poster_png":
            return _STUB_PNG
        return _STUB_PDF


def get_render_engine() -> BaseRenderEngine:
    """Return the configured render engine instance."""
    backend = getattr(settings, "RENDER_BACKEND", "playwright")
    if backend == "stub":
        return StubRenderEngine()
    try:
        import playwright  # noqa: F401, PLC0415
    except ImportError:
        logger.warning(
            "RENDER_BACKEND=playwright but playwright is not installed — "
            "falling back to stub engine"
        )
        return StubRenderEngine()
    return PlaywrightRenderEngine()
