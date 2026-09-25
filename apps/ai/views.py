"""
AI app views — Phase 5A (voice upload & transcription display).

Endpoints:
  GET  /ai/voice/                 — voice notes list + standalone upload form
  POST /ai/voice/upload/          — HTMX upload (audio file; optional listing pk)
  GET  /ai/voice/<pk>/status/     — HTMX partial for status polling
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.ai.models import VoiceDraft, VoiceNote
from apps.ai.services import (
    apply_draft_to_listing,
    create_voice_note,
    enqueue_transcription,
    extract_draft,
    get_draft_provider_for_agency,
)
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
    return HttpResponse(
        render_to_string(
            "ai/partials/voice_note_item.html",
            {"note": note},
            request=request,
        )
    )


@login_required
@require_POST
def voice_note_retry_view(request, pk: int) -> HttpResponse:
    """HTMX: re-queue a failed voice note for transcription."""
    note = get_object_or_404(VoiceNote, pk=pk, agency=request.user.agency)
    enqueue_transcription(note)
    return HttpResponse(
        render_to_string(
            "ai/partials/voice_note_item.html",
            {"note": note},
            request=request,
        )
    )


@login_required
def voice_note_detail_view(request, pk: int) -> HttpResponse:
    """Detail page: transcript (and, in Phase 5B, the extracted draft)."""
    note = get_object_or_404(
        VoiceNote.objects.select_related("listing", "uploaded_by"),
        pk=pk,
        agency=request.user.agency,
    )
    return render(
        request,
        "ai/voice_note_detail.html",
        {"note": note, "draft": getattr(note, "draft", None)},
    )


@login_required
@require_POST
def draft_generate_view(request, pk: int) -> HttpResponse:
    """
    HTMX: extract a structured draft from a transcribed voice note.

    Regex provider (offline) → immediate fields partial.
    LLM provider (Gemini) → Celery task + pending partial with polling.
    """
    note = get_object_or_404(VoiceNote, pk=pk, agency=request.user.agency)
    provider = get_draft_provider_for_agency(request.user.agency)

    if provider.is_async:
        from apps.ai.tasks import extract_draft_task

        extract_draft_task.delay(note.pk)
        return HttpResponse(
            render_to_string(
                "ai/partials/draft_pending.html",
                {"note": note},
                request=request,
            ),
            status=202,
        )

    try:
        draft = extract_draft(note, provider)
    except ValidationError as exc:
        return HttpResponse(_error_html(" ".join(exc.messages)), status=422)
    html = render_to_string(
        "ai/partials/draft_fields.html",
        {"note": note, "draft": draft},
        request=request,
    )
    return HttpResponse(html)


@login_required
def draft_status_view(request, pk: int) -> HttpResponse:
    """HTMX polling target: fields partial once the draft exists, else pending."""
    note = get_object_or_404(VoiceNote, pk=pk, agency=request.user.agency)
    draft = VoiceDraft.objects.filter(voice_note=note).first()
    if draft is not None:
        template = "ai/partials/draft_fields.html"
        status = 200
    else:
        template = "ai/partials/draft_pending.html"
        status = 202
    return HttpResponse(
        render_to_string(
            template,
            {"note": note, "draft": draft},
            request=request,
        ),
        status=status,
    )


@login_required
@require_POST
def draft_apply_view(request, pk: int) -> HttpResponse:
    """Apply the extracted draft: create a Listing and redirect to it."""
    draft = get_object_or_404(
        VoiceDraft.objects.select_related("voice_note"),
        pk=pk,
        agency=request.user.agency,
    )
    if draft.status == "applied":
        return redirect("listings:detail", draft.listing.pk)
    listing = apply_draft_to_listing(draft, request.user)
    messages.success(
        request, f"فایل «{listing.code}» از پیش‌نویس صوتی ساخته شد."
    )
    return redirect("listings:update", listing.pk)


def _error_html(message: str) -> str:
    from django.utils.html import escape

    return (
        f'<p class="text-sm" style="color:var(--red)" role="alert">{escape(message)}</p>'
    )
