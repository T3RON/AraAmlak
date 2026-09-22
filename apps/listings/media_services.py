"""
Media service — Phase 1C.

Business logic for media upload, MIME validation, EXIF stripping,
thumbnail + WebP generation, signed URL access.

All heavy processing (Pillow ops) is dispatched to Celery.
This module is pure Python — no HTTP request objects.
"""

import io
import logging

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.listings.models import (
    ALLOWED_MIMES_BY_TYPE,
    MAX_UPLOAD_SIZE_BYTES,
    Media,
    MediaStatus,
    MediaType,
)

logger = logging.getLogger(__name__)

# Thumbnail dimensions (width × height)
THUMB_SIZE = (400, 300)
# WebP max dimension (longer side)
WEBP_MAX_SIZE = 1600


# ─── MIME detection ───────────────────────────────────────────────────────────

_MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": None,  # could be webp or avi — need extra check
    b"\x00\x00\x00\x18ftyp": "video/mp4",
    b"\x00\x00\x00\x20ftyp": "video/mp4",
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    b"\x1a\x45\xdf\xa3": "video/webm",
    b"ftypM4V": "video/mp4",
}

_FTYP_VIDEO = {b"isom", b"iso2", b"avc1", b"mp41", b"mp42", b"M4V ", b"qt  "}


def detect_mime(data: bytes) -> str:
    """
    Detect MIME from the first 12 bytes of file content.
    Returns a best-guess MIME string or 'application/octet-stream'.
    """
    for magic, mime in _MAGIC.items():
        if data[: len(magic)] == magic:
            if mime is not None:
                return mime
            # RIFF check: webp vs avi
            if data[:4] == b"RIFF":
                if data[8:12] == b"WEBP":
                    return "image/webp"
                return "video/x-msvideo"
            break
    # Try ftyp box for mov/mp4 variations
    if data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in _FTYP_VIDEO:
            return "video/mp4"
        if brand in {b"qt  "}:
            return "video/quicktime"
    # heic / heif
    if data[4:8] == b"ftyp" and data[8:12] in {b"heic", b"heix", b"mif1", b"msf1"}:
        return "image/heic"
    return "application/octet-stream"


# ─── Validation ───────────────────────────────────────────────────────────────


def validate_upload(uploaded_file, media_type: str) -> str:
    """
    Validate an uploaded file (size + real MIME).
    Returns the detected MIME string.
    Raises ValidationError on failure.
    """
    size = uploaded_file.size
    max_size = MAX_UPLOAD_SIZE_BYTES.get(media_type, 20 * 1024 * 1024)
    if size > max_size:
        max_mb = max_size // (1024 * 1024)
        raise ValidationError(
            _("حجم فایل از %(max)s مگابایت بیشتر است.") % {"max": max_mb}
        )

    # Read first 16 bytes for magic detection
    uploaded_file.seek(0)
    header = uploaded_file.read(16)
    uploaded_file.seek(0)

    mime = detect_mime(header)
    allowed = ALLOWED_MIMES_BY_TYPE.get(media_type, frozenset())
    if mime not in allowed:
        raise ValidationError(
            _("نوع فایل «%(mime)s» برای %(type)s مجاز نیست.") % {
                "mime": mime,
                "type": media_type,
            }
        )
    return mime


# ─── EXIF stripping ───────────────────────────────────────────────────────────


def strip_exif_from_bytes(image_bytes: bytes) -> bytes:
    """
    Remove all EXIF / IPTC / XMP metadata from JPEG bytes using Pillow.
    For non-JPEG (PNG, WebP, GIF) just re-save without extra metadata.
    Returns cleaned image bytes.

    Called from Celery task — import Pillow lazily to keep this module
    importable without PIL installed (e.g. pure unit tests).
    """
    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError:
        logger.warning("Pillow not installed — EXIF stripping skipped")
        return image_bytes

    buf_in = io.BytesIO(image_bytes)
    try:
        img_obj = Image.open(buf_in)
    except Exception:  # noqa: BLE001
        # Not a recognisable image; return bytes unchanged
        return image_bytes

    with img_obj as img:
        # Convert to RGB to drop alpha issues and ensure uniform saving
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGBA")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        fmt = img.format or "JPEG"
        buf_out = io.BytesIO()
        # Re-save without passing exif/icc_profile
        if fmt == "JPEG":
            img.save(buf_out, format="JPEG", quality=92, optimize=True, exif=b"")
        elif fmt == "PNG":
            img.save(buf_out, format="PNG", optimize=True)
        elif fmt == "WEBP":
            img.save(buf_out, format="WEBP", quality=88, exif=b"")
        else:
            img.save(buf_out, format="JPEG", quality=92, optimize=True, exif=b"")
        return buf_out.getvalue()


# ─── Thumbnail + WebP generation ─────────────────────────────────────────────


def _make_thumbnail(img, size: tuple) -> bytes:
    """Create a JPEG thumbnail. Input: PIL Image."""
    thumb = img.copy()
    thumb.thumbnail(size)
    buf = io.BytesIO()
    thumb.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()


def _make_webp(img, max_dim: int) -> bytes:
    """Create a WebP version scaled so longest side ≤ max_dim."""
    w, h = img.size
    if max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        img = img.resize(new_size)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=85, method=4)
    return buf.getvalue()


def process_photo(media_id: int) -> None:
    """
    Main processing pipeline for a photo Media record.

    1. Load original file bytes.
    2. Strip EXIF.
    3. Generate JPEG thumbnail (400×300).
    4. Generate WebP version (max 1600px).
    5. Save cleaned file back, set thumbnail + webp fields.
    6. Mark status = READY.

    Designed to run inside Celery. Re-entrant: if status is already READY, skip.
    """
    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError:
        logger.error("Pillow not installed — cannot process photo %s", media_id)
        _mark_error(media_id, "Pillow not installed")
        return

    try:
        media = Media.objects.get(pk=media_id)
    except Media.DoesNotExist:
        logger.warning("Media %s not found for processing", media_id)
        return

    if media.status == MediaStatus.READY:
        return

    Media.objects.filter(pk=media_id).update(status=MediaStatus.PROCESSING)

    try:
        # Read from storage
        media.file.open("rb")
        raw = media.file.read()
        media.file.close()

        # Strip EXIF
        clean_bytes = strip_exif_from_bytes(raw)

        # Open with Pillow for thumbnail / webp
        pil_img = Image.open(io.BytesIO(clean_bytes))
        if pil_img.mode in ("RGBA", "P"):
            pil_img = pil_img.convert("RGB")
        elif pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        thumb_bytes = _make_thumbnail(pil_img, THUMB_SIZE)
        webp_bytes = _make_webp(pil_img, WEBP_MAX_SIZE)

        base_name = f"{media_id}"

        with transaction.atomic():
            media.refresh_from_db()

            # Save cleaned original back
            media.file.save(
                media.file.name.split("/")[-1],
                ContentFile(clean_bytes),
                save=False,
            )
            media.thumbnail.save(
                f"thumb_{base_name}.jpg",
                ContentFile(thumb_bytes),
                save=False,
            )
            media.webp.save(
                f"webp_{base_name}.webp",
                ContentFile(webp_bytes),
                save=False,
            )
            media.status = MediaStatus.READY
            media.save(update_fields=["file", "thumbnail", "webp", "status"])

        logger.info("Media %s processed successfully", media_id)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Error processing media %s: %s", media_id, exc)
        _mark_error(media_id, str(exc)[:500])


def _mark_error(media_id: int, message: str) -> None:
    Media.objects.filter(pk=media_id).update(
        status=MediaStatus.ERROR,
        error_message=message,
    )


# ─── Upload entry point ───────────────────────────────────────────────────────


@transaction.atomic
def create_media(
    listing,
    uploaded_file,
    media_type: str = MediaType.PHOTO,
    is_private: bool = False,
    caption: str = "",
    uploaded_by=None,
) -> Media:
    """
    Validate, save and enqueue a media file.
    Returns the saved Media instance (status=PENDING).
    The Celery task `process_media_task` is dispatched after commit.
    """
    mime = validate_upload(uploaded_file, media_type)

    # Compute order: one more than max existing order for this listing
    from django.db.models import Max  # noqa: PLC0415
    max_order = Media.objects.filter(listing=listing).aggregate(m=Max("order"))["m"]
    order = (max_order or 0) + 1

    # If no cover yet and this is a photo, make it the cover
    already_has_cover = Media.objects.filter(
        listing=listing, media_type=MediaType.PHOTO, is_cover=True
    ).exists()
    is_cover = media_type == MediaType.PHOTO and not already_has_cover

    media = Media(
        listing=listing,
        media_type=media_type,
        is_private=is_private or (media_type == MediaType.DOCUMENT),
        caption=caption,
        order=order,
        is_cover=is_cover,
        original_filename=uploaded_file.name[:300],
        mime_type=mime,
        file_size=uploaded_file.size,
        uploaded_by=uploaded_by,
        status=MediaStatus.PENDING,
    )
    media.file = uploaded_file
    media.save()

    # Dispatch Celery task only for photos (video/docs just stored as-is)
    if media_type == MediaType.PHOTO:
        from apps.listings.tasks import process_media_task  # noqa: PLC0415
        transaction.on_commit(lambda: process_media_task.delay(media.pk))

    return media


def delete_media(media: Media) -> None:
    """Delete a media object and its storage files."""
    # Delete actual files from storage
    for field_name in ("file", "thumbnail", "webp"):
        f = getattr(media, field_name)
        if f:
            try:
                f.delete(save=False)
            except Exception:  # noqa: BLE001
                logger.warning("Could not delete storage file for media %s", media.pk)
    media.delete()


def reorder_media(listing, ordered_ids: list[int]) -> None:
    """
    Update the order of media files for a listing.
    ordered_ids: list of Media PKs in desired display order.
    """
    for idx, media_id in enumerate(ordered_ids):
        Media.objects.filter(pk=media_id, listing=listing).update(order=idx)


def set_cover(listing, media_id: int) -> None:
    """Set a photo as the cover image; unset all others."""
    with transaction.atomic():
        Media.objects.filter(listing=listing, media_type=MediaType.PHOTO).update(is_cover=False)
        Media.objects.filter(pk=media_id, listing=listing, media_type=MediaType.PHOTO).update(
            is_cover=True
        )
