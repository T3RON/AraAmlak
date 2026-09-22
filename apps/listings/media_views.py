"""
Media views — Phase 1C.

Endpoints:
  POST   /listings/<pk>/media/upload/          — upload one or more files (HTMX)
  POST   /listings/<pk>/media/<media_pk>/delete/ — delete a media file (HTMX)
  POST   /listings/<pk>/media/reorder/          — reorder (drag & drop, HTMX)
  POST   /listings/<pk>/media/<media_pk>/cover/ — set as cover photo (HTMX)
  GET    /listings/media/private/<token>/       — serve private doc via signed URL
"""

import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.signing import BadSignature, SignatureExpired
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.listings.media_services import create_media, delete_media, reorder_media, set_cover
from apps.listings.models import Listing, Media, MediaType

logger = logging.getLogger(__name__)


def _get_listing_for_user(pk, user):
    """Return a Listing that belongs to the user's agency, or 404."""
    return get_object_or_404(Listing, pk=pk, agency=user.agency)


@login_required
@require_POST
def media_upload_view(request, pk: int) -> HttpResponse:
    """
    HTMX endpoint: upload one file per request (call multiple times for multi-upload).
    Returns a partial HTML row/card for the new media item.
    """
    listing = _get_listing_for_user(pk, request.user)
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return HttpResponse(_error_html("فایلی دریافت نشد."), status=400)

    media_type = request.POST.get("media_type", MediaType.PHOTO)
    is_private = request.POST.get("is_private", "false").lower() == "true"
    caption = request.POST.get("caption", "")

    try:
        media = create_media(
            listing=listing,
            uploaded_file=uploaded_file,
            media_type=media_type,
            is_private=is_private,
            caption=caption,
            uploaded_by=request.user,
        )
    except ValidationError as exc:
        return HttpResponse(_error_html(" ".join(exc.messages)), status=422)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during media upload: %s", exc)
        return HttpResponse(_error_html("خطای داخلی رخ داد."), status=500)

    html = render_to_string(
        "listings/partials/media_item.html",
        {"media": media, "listing": listing},
        request=request,
    )
    return HttpResponse(html, status=201)


@login_required
@require_POST
def media_delete_view(request, pk: int, media_pk: int) -> HttpResponse:
    """HTMX: delete a media item and return empty 200 (HTMX will swap-oob remove it)."""
    listing = _get_listing_for_user(pk, request.user)
    media = get_object_or_404(Media, pk=media_pk, listing=listing)
    delete_media(media)
    return HttpResponse(status=204)


@login_required
@require_POST
def media_reorder_view(request, pk: int) -> HttpResponse:
    """
    HTMX: reorder media items.
    Expects POST body: `order[]=<id1>&order[]=<id2>...`
    """
    listing = _get_listing_for_user(pk, request.user)
    raw_ids = request.POST.getlist("order[]")
    try:
        ordered_ids = [int(i) for i in raw_ids]
    except (ValueError, TypeError):
        return HttpResponse("پارامتر نامعتبر", status=400)
    reorder_media(listing, ordered_ids)
    return HttpResponse(status=200)


@login_required
@require_POST
def media_set_cover_view(request, pk: int, media_pk: int) -> HttpResponse:
    """HTMX: set photo as cover. Returns updated media gallery partial."""
    listing = _get_listing_for_user(pk, request.user)
    set_cover(listing, media_pk)
    # Re-render the full media gallery so cover indicators update
    media_qs = Media.objects.filter(listing=listing).order_by("order", "created_at")
    html = render_to_string(
        "listings/partials/media_gallery.html",
        {"listing": listing, "media_list": media_qs},
        request=request,
    )
    return HttpResponse(html)


def media_serve_private(request, token: str) -> HttpResponse:
    """
    Serve a private document via a signed URL token.
    No login required (the signed token IS the credential).
    Token is time-limited (default 300s).
    """
    from django.core import signing  # noqa: PLC0415

    try:
        data = signing.loads(token, salt="media-signed-url", max_age=300)
    except SignatureExpired as exc:
        raise Http404("لینک منقضی شده است.") from exc
    except BadSignature as exc:
        raise Http404("لینک نامعتبر است.") from exc

    media_id = data.get("media_id")
    if not media_id:
        raise Http404

    media = get_object_or_404(Media, pk=media_id, is_private=True)

    if not media.file:
        raise Http404

    # Stream file contents
    try:
        media.file.open("rb")
        content = media.file.read()
        media.file.close()
    except Exception as exc:  # noqa: BLE001
        raise Http404 from exc

    content_type = media.mime_type or "application/octet-stream"
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = (
        f'inline; filename="{media.original_filename or "document"}"'
    )
    return response


def _error_html(msg: str) -> str:
    return f'<p class="text-red-500 text-sm">{msg}</p>'
