"""
Import views — Phase 1D.

Endpoints:
  GET/POST  /listings/import/           — upload form + job list
  GET       /listings/import/<pk>/      — job status + error report
  GET       /listings/import/<pk>/progress/ — HTMX polling partial (status badge)
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from apps.core.models import get_current_agency
from apps.listings.models import ImportJob, ImportJobStatus

logger = logging.getLogger(__name__)

_ALLOWED_IMPORT_MIME = frozenset([
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.ms-excel",  # xls
    "text/csv",
    "text/plain",
    "application/octet-stream",  # some browsers send this for xlsx
])

_MAX_IMPORT_SIZE = 10 * 1024 * 1024  # 10 MB


@login_required
@require_http_methods(["GET", "POST"])
def import_list_view(request):
    """Upload form + list of recent import jobs."""
    agency = get_current_agency()

    if request.method == "POST":
        uploaded = request.FILES.get("file")
        if not uploaded:
            return render(request, "listings/import.html", {
                "error": "فایلی انتخاب نشده است.",
                "jobs": _recent_jobs(agency),
            })

        if uploaded.size > _MAX_IMPORT_SIZE:
            return render(request, "listings/import.html", {
                "error": "حجم فایل از ۱۰ مگابایت بیشتر است.",
                "jobs": _recent_jobs(agency),
            })

        job = ImportJob.objects.create(
            agency=agency,
            uploaded_file=uploaded,
            original_filename=uploaded.name[:300],
            created_by=request.user,
        )

        # Dispatch Celery task
        from django.db import transaction  # noqa: PLC0415

        from apps.listings.tasks import run_import_job_task  # noqa: PLC0415
        transaction.on_commit(lambda: run_import_job_task.delay(job.pk))

        return redirect("listings:import_detail", pk=job.pk)

    return render(request, "listings/import.html", {
        "jobs": _recent_jobs(agency),
    })


@login_required
def import_detail_view(request, pk: int):
    """Show import job status and error report."""
    agency = get_current_agency()
    job = get_object_or_404(ImportJob, pk=pk, agency=agency)
    return render(request, "listings/import_detail.html", {"job": job})


@login_required
def import_progress_view(request, pk: int):
    """HTMX polling endpoint — returns a small status partial."""
    agency = get_current_agency()
    job = get_object_or_404(ImportJob, pk=pk, agency=agency)
    html = render_to_string(
        "listings/partials/import_status.html",
        {"job": job},
        request=request,
    )
    resp = HttpResponse(html)
    # If still running, tell HTMX to keep polling every 2s
    if job.status in (ImportJobStatus.PENDING, ImportJobStatus.PROCESSING):
        resp["HX-Trigger"] = '{"pollImport": null}'
    return resp


def _recent_jobs(agency):
    return ImportJob.objects.filter(agency=agency).order_by("-created_at")[:20]
