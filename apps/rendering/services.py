"""
Rendering service layer — Phase 6A.

Public API:
- render_poster_html(listing)
    Builds the self-contained poster HTML (cover/logo as base64 data URIs).

- enqueue_render(listing, kind)
    Creates a pending RenderJob and fires the Celery render task.

- run_render(job_id)
    Called by the Celery task; renders via the configured engine and
    stores the output file on the job.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

from apps.rendering.models import RenderJob, RenderStatus

if TYPE_CHECKING:
    from apps.listings.models import Listing
    from apps.listings.models import Media as MediaModel

logger = logging.getLogger(__name__)


# ─── Poster context ───────────────────────────────────────────────────────────

_IMAGE_MIMES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

# Poster embeds its own fonts so headless rendering works on hosts without
# Persian system fonts (e.g. plain Docker images).
_POSTER_FONTS = [
    ("font_regular_uri", "fonts/Vazirmatn-Regular.woff2"),
    ("font_bold_uri", "fonts/Vazirmatn-Bold.woff2"),
    ("font_xbold_uri", "fonts/Vazirmatn-ExtraBold.woff2"),
]


def _font_data_uris() -> dict:
    """Read self-hosted Vazirmatn fonts and encode them as data URIs.

    Fonts are read straight from BASE_DIR/static (shipped in the repo) —
    not via staticfiles finders, which depend on STATICFILES_DIRS being
    configured in every settings module.
    """
    uris = {}
    for key, relpath in _POSTER_FONTS:
        path = Path(settings.BASE_DIR) / "static" / relpath
        if not path.is_file():
            logger.warning(
                "Poster font not found: %s — falling back to system fonts", relpath
            )
            uris[key] = ""
            continue
        with open(path, "rb") as fh:
            data = base64.b64encode(fh.read()).decode("ascii")
        uris[key] = f"data:font/woff2;base64,{data}"
    return uris


def _guess_image_mime(name: str) -> str:
    from pathlib import Path

    return _IMAGE_MIMES.get(Path(name).suffix.lower(), "image/jpeg")


def _file_to_data_uri(field_file, mime: str = "") -> str:
    """
    Encode a stored image (Media.file or Agency.logo FieldFile) as a base64
    data URI. Returns "" when there is no file — the poster must render
    without images, never crash on them.
    """
    if field_file is None:
        return ""
    try:
        with field_file.open("rb") as fh:
            data = fh.read()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load image %r for poster: %s", field_file, exc)
        return ""
    if not data:
        return ""
    mime = mime or _guess_image_mime(getattr(field_file, "name", ""))
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def get_cover_media(listing: Listing) -> MediaModel | None:
    """Cover photo for the poster (is_cover first, then order)."""
    return (
        listing.media_files.filter(media_type="photo", is_private=False)
        .order_by("-is_cover", "order", "created_at")
        .first()
    )


def render_poster_html(listing: Listing) -> str:
    """Render the poster template to a self-contained HTML string."""
    from apps.core.currency import format_number_fa, format_toman

    cover = get_cover_media(listing)
    agency_logo = getattr(listing.agency, "logo", None)

    price_lines = []
    if listing.sale_price:
        price_lines.append(format_toman(listing.sale_price))
    if listing.mortgage_amount:
        price_lines.append("رهن " + format_toman(listing.mortgage_amount))
    if listing.rent_amount:
        price_lines.append("اجاره " + format_toman(listing.rent_amount))

    html = render_to_string(
        "rendering/poster.html",
        {
            "listing": listing,
            "agency": listing.agency,
            "cover_data_uri": _file_to_data_uri(
                cover.file if cover else None, cover.mime_type if cover else ""
            ),
            "logo_data_uri": _file_to_data_uri(agency_logo),
            "price_lines": price_lines,
            "area_str": format_number_fa(listing.area) if listing.area else "",
            "rooms_str": format_number_fa(listing.rooms) if listing.rooms else "",
            **_font_data_uris(),
        },
    )
    return html


# ─── Enqueue ──────────────────────────────────────────────────────────────────


def enqueue_render(listing: Listing, kind: str = "poster_pdf") -> RenderJob:
    """Create a pending RenderJob and dispatch the Celery render task."""
    from apps.rendering.tasks import render_poster_task

    job = RenderJob.objects.create(
        agency=listing.agency,
        listing=listing,
        kind=kind,
    )
    render_poster_task.delay(job.pk)
    return job


# ─── Render (called by Celery task) ───────────────────────────────────────────


def run_render(job_id: int) -> None:
    """
    Render the poster and store the output file on the job.

    State machine: pending/failed → running → success (or failed).
    Raises on error so the Celery task can retry with backoff.
    """
    from apps.rendering.engines import get_render_engine

    job = RenderJob.all_objects.select_related("listing", "listing__agency").get(
        pk=job_id
    )

    if job.status == RenderStatus.SUCCESS:
        return  # idempotent guard

    job.status = RenderStatus.RUNNING
    job.save(update_fields=["status", "updated_at"])

    try:
        engine = get_render_engine()
        html = render_poster_html(job.listing)
        output = engine.render(html, job.kind)

        ext = ".png" if job.kind == "poster_png" else ".pdf"
        job.file.save(f"poster{ext}", ContentFile(output), save=False)
        job.engine = engine.name
        job.status = RenderStatus.SUCCESS
        job.error_message = ""
        job.rendered_at = timezone.now()
        job.save(
            update_fields=[
                "file",
                "engine",
                "status",
                "error_message",
                "rendered_at",
                "updated_at",
            ]
        )
        logger.info("RenderJob #%d rendered via %s (%d bytes)", job_id, engine.name, len(output))
    except Exception as exc:
        job.status = RenderStatus.FAILED
        job.error_message = str(exc)[:500]
        job.save(update_fields=["status", "error_message", "updated_at"])
        logger.error("RenderJob #%d failed: %s", job_id, exc)
        raise
