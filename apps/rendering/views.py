"""
Rendering app views — Phase 6A.

Endpoints:
  GET  /rendering/listings/<pk>/jobs/          — job list + render button
  POST /rendering/listings/<pk>/jobs/create/   — enqueue a render job (HTMX or form)
  GET  /rendering/jobs/<pk>/download/          — download the rendered file
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.listings.models import Listing
from apps.rendering.models import RenderJob

logger = logging.getLogger(__name__)


def _get_listing_for_user(pk: int, user) -> Listing:
    """Return a Listing that belongs to the user's agency, or 404."""
    return get_object_or_404(Listing, pk=pk, agency=user.agency)


@login_required
def render_job_list_view(request, pk: int) -> HttpResponse:
    """Render jobs page for one listing (with render button)."""
    listing = _get_listing_for_user(pk, request.user)
    jobs = listing.render_jobs.all()[:20]
    return render(
        request,
        "rendering/render_job_list.html",
        {"listing": listing, "jobs": jobs},
    )


@login_required
@require_POST
def render_job_create_view(request, pk: int) -> HttpResponse:
    """HTMX/form endpoint: enqueue a poster render job for the listing."""
    listing = _get_listing_for_user(pk, request.user)
    kind = request.POST.get("kind", "poster_pdf")
    if kind not in ("poster_pdf", "poster_png"):
        kind = "poster_pdf"

    from apps.rendering.services import enqueue_render

    job = enqueue_render(listing, kind)

    if request.headers.get("HX-Request"):
        html = render_to_string(
            "rendering/partials/render_job_item.html",
            {"job": job},
            request=request,
        )
        return HttpResponse(html, status=201)
    return redirect("rendering:job_list", listing.pk)


@login_required
def render_job_download_view(request, job_pk: int) -> HttpResponse:
    """Serve the rendered poster file (scoped to the user's agency)."""
    job = get_object_or_404(RenderJob, pk=job_pk, agency=request.user.agency)
    if not job.file:
        return HttpResponse("فایل خروجی هنوز آماده نیست.", status=404)
    ext = job.file.name.rsplit(".", 1)[-1]
    kind = job.kind.replace("poster_", "")
    return FileResponse(
        job.file.open("rb"),
        as_attachment=True,
        filename=f"poster-{job.listing.code}-{kind}.{ext}",
    )


@login_required
def render_job_status_view(request, job_pk: int) -> HttpResponse:
    """HTMX partial: current job row (used for polling while rendering)."""
    job = get_object_or_404(
        RenderJob.objects.select_related("listing"), pk=job_pk, agency=request.user.agency
    )
    return HttpResponse(
        render_to_string(
            "rendering/partials/render_job_item.html",
            {"job": job},
            request=request,
        )
    )
