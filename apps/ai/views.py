"""
AI app views — Phase 5A (voice upload & transcription display).

Endpoints:
  GET  /ai/voice/                 — voice notes list + standalone upload form
  POST /ai/voice/upload/          — HTMX upload (audio file; optional listing pk)
  GET  /ai/voice/<pk>/status/     — HTMX partial for status polling
"""

import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.ai.models import VoiceNote
from apps.ai.services import create_voice_note, enqueue_transcription
from apps.listings.models import Listing

logger = logging.getLogger(__name__)


@login_required
def voice_note_list_view(request) -> HttpResponse:
    """Voice notes page: standalone upload form + agency's notes."""
    notes = VoiceNote.objects.select_related("listing", "uploaded_by")[:50]
    return render(request, "ai/voice_note_list.html", {"voice_notes": notes})


@login_required
@require_POST
def voice_note_upload_view(request) -> HttpResponse:
    """
    HTMX endpoint: upload an audio file, queue it for transcription and
    return the note's HTML row. `listing` (pk) is optional.
    """
    listing = None
    listing_pk = request.POST.get("listing")
    if listing_pk:
        listing = get_object_or_404(Listing, pk=listing_pk, agency=request.user.agency)

    uploaded_file = request.FILES.get("audio")
    if not uploaded_file:
        return HttpResponse(_error_html("فایل صوتی دریافت نشد."), status=400)

    try:
        note = create_voice_note(
            agency=request.user.agency,
            uploaded_file=uploaded_file,
            listing=listing,
            uploaded_by=request.user,
        )
    except ValidationError as exc:
        return HttpResponse(_error_html(" ".join(exc.messages)), status=422)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during voice upload: %s", exc)
        return HttpResponse(_error_html("خطای داخلی رخ داد."), status=500)

    enqueue_transcription(note)
    html = render_to_string(
        "ai/partials/voice_note_item.html",
        {"note": note},
        request=request,
    )
    return HttpResponse(html, status=201)


@login_required
def voice_note_status_view(request, pk: int) -> HttpResponse:
    """HTMX partial: current state of a voice note (used for polling)."""
    note = get_object_or_404(
        VoiceNote.objects.select_related("listing"), pk=pk, agency=request.user.agency
    )
    return render_to_string(
        "ai/partials/voice_note_item.html",
        {"note": note},
        request=request,
    )


@login_required
@require_POST
def voice_note_retry_view(request, pk: int) -> HttpResponse:
    """HTMX: re-queue a failed voice note for transcription."""
    note = get_object_or_404(VoiceNote, pk=pk, agency=request.user.agency)
    enqueue_transcription(note)
    return render_to_string(
        "ai/partials/voice_note_item.html",
        {"note": note},
        request=request,
    )


@login_required
def voice_note_detail_view(request, pk: int) -> HttpResponse:
    """Detail page: transcript (and, in Phase 5B, the extracted draft)."""
    note = get_object_or_404(
        VoiceNote.objects.select_related("listing", "uploaded_by"),
        pk=pk,
        agency=request.user.agency,
    )
    return render(request, "ai/voice_note_detail.html", {"note": note})


def _error_html(message: str) -> str:
    from django.utils.html import escape

    return (
        f'<p class="text-sm" style="color:var(--red)" role="alert">{escape(message)}</p>'
    )
