"""
Tests for Phase 6A — Poster render (Playwright PDF/PNG).

Coverage:
- StubRenderEngine (valid minimal bytes)
- get_render_engine backend selection
- render_poster_html (self-contained HTML, cover data URI, prices)
- enqueue_render + run_render pipeline (state machine with stub)
- Real Playwright render (skipped when Chromium unavailable)
- Celery task dispatch
- Views: job list, create (HTMX + form), download, status
- Tenant isolation: agency B cannot touch agency A jobs
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.rendering.engines import StubRenderEngine, get_render_engine
from apps.rendering.models import RenderJob, RenderStatus

# ─── Helpers & fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def listing(db, agency):
    from apps.listings.models import DealType, Listing, PropertyType

    return Listing.objects.create(
        agency=agency,
        property_type=PropertyType.APARTMENT,
        deal_type=DealType.SALE,
        title="آپارتمان تست پوستر",
        city="تهران",
        area=80,
        rooms=2,
        floor=3,
        total_floors=5,
        build_year=2011,
        sale_price=2_700_000_000,
        parking=True,
        elevator=True,
        status="active",
    )


@pytest.fixture
def render_job(db, agency, listing):
    return RenderJob.objects.create(agency=agency, listing=listing)


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:  # noqa: BLE001
        return False


CHROMIUM_OK = _chromium_available()


# ─── Engines ──────────────────────────────────────────────────────────────────


class TestStubEngine:
    def test_pdf_bytes(self):
        output = StubRenderEngine().render("<html></html>", "poster_pdf")
        assert output.startswith(b"%PDF")

    def test_png_bytes(self):
        output = StubRenderEngine().render("<html></html>", "poster_png")
        assert output.startswith(b"\x89PNG")


class TestGetRenderEngine:
    def test_default_is_playwright(self):
        from apps.rendering.engines import PlaywrightRenderEngine

        engine = get_render_engine()
        assert isinstance(engine, PlaywrightRenderEngine)

    @override_settings(RENDER_BACKEND="stub")
    def test_stub_backend(self):
        engine = get_render_engine()
        assert isinstance(engine, StubRenderEngine)


# ─── Poster HTML ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPosterHTML:
    def test_contains_listing_data(self, listing):
        from apps.core.currency import to_persian_digits
        from apps.rendering.services import render_poster_html

        html = render_poster_html(listing)
        assert "آپارتمان تست پوستر" in html
        assert "۲ میلیارد و ۷۰۰ میلیون تومان" in html  # format_toman
        assert to_persian_digits(listing.code) in html  # code in Persian digits
        assert listing.agency.name in html

    def test_cover_as_data_uri(self, agency, listing):
        from apps.listings.models import Media, MediaType
        from apps.rendering.services import render_poster_html

        photo = SimpleUploadedFile(
            "cover.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 20, content_type="image/jpeg"
        )
        Media.objects.create(
            listing=listing,
            media_type=MediaType.PHOTO,
            file=photo,
            is_cover=True,
            mime_type="image/jpeg",
        )
        html = render_poster_html(listing)
        assert "data:image/jpeg;base64," in html

    def test_without_cover_renders_placeholder(self, listing):
        from apps.rendering.services import render_poster_html

        html = render_poster_html(listing)
        assert "cover-placeholder" in html
        assert "data:image" not in html


@pytest.mark.django_db
class TestPosterFonts:
    def test_fonts_embedded_as_data_uris(self, listing):
        from apps.rendering.services import render_poster_html

        html = render_poster_html(listing)
        assert html.count("@font-face") == 3  # regular + bold + extra-bold
        assert "data:font/woff2;base64," in html

    def test_missing_fonts_render_without_face(self, listing):
        from unittest.mock import patch

        from apps.rendering.services import render_poster_html

        with patch(
            "apps.rendering.services._POSTER_FONTS",
            [("font_regular_uri", "fonts/Nope.woff2")],
        ):
            html = render_poster_html(listing)
        assert "@font-face" not in html  # graceful fallback to system fonts
        assert "آپارتمان تست پوستر" in html


# ─── Pipeline (stub engine) ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestRenderPipeline:
    def test_enqueue_creates_pending_job(self, listing):
        with patch("apps.rendering.tasks.render_poster_task.delay") as mock_delay:
            job = _enqueue(listing)

        assert job.status == RenderStatus.PENDING
        assert job.kind == "poster_pdf"
        mock_delay.assert_called_once_with(job.pk)

    def test_run_render_success(self, render_job, settings):
        settings.RENDER_BACKEND = "stub"
        from apps.rendering.services import run_render

        run_render(render_job.pk)
        render_job.refresh_from_db()

        assert render_job.status == RenderStatus.SUCCESS
        assert render_job.engine == "stub"
        assert render_job.file.name.endswith(".pdf")
        assert render_job.rendered_at is not None
        with render_job.file.open("rb") as fh:
            assert fh.read().startswith(b"%PDF")

    def test_run_render_png(self, db, agency, listing, settings):
        settings.RENDER_BACKEND = "stub"
        from apps.rendering.services import run_render

        job = RenderJob.objects.create(
            agency=agency, listing=listing, kind="poster_png"
        )
        run_render(job.pk)
        job.refresh_from_db()
        assert job.file.name.endswith(".png")

    def test_run_render_idempotent(self, render_job):
        from apps.rendering.services import run_render

        render_job.status = RenderStatus.SUCCESS
        render_job.save()
        run_render(render_job.pk)  # no-op, no crash
        render_job.refresh_from_db()
        assert render_job.status == RenderStatus.SUCCESS

    def test_engine_failure_marks_failed_and_reraises(self, render_job):
        from apps.rendering.services import run_render

        with patch("apps.rendering.engines.get_render_engine") as mock_get:
            mock_get.return_value.render.side_effect = RuntimeError("browser died")
            with pytest.raises(RuntimeError, match="browser died"):
                run_render(render_job.pk)

        render_job.refresh_from_db()
        assert render_job.status == RenderStatus.FAILED
        assert "browser died" in render_job.error_message

    def test_task_calls_service(self, render_job):
        from apps.rendering.tasks import render_poster_task

        with patch("apps.rendering.services.run_render") as mock_run:
            render_poster_task.apply(args=[render_job.pk])
        mock_run.assert_called_once_with(render_job.pk)


def _enqueue(listing):
    from apps.rendering.services import enqueue_render

    return enqueue_render(listing)


# ─── Real Playwright render ───────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.skipif(not CHROMIUM_OK, reason="Playwright Chromium not available")
class TestRealPlaywrightRender:
    def test_pdf_render(self, render_job):
        from apps.rendering.services import run_render

        with override_settings(RENDER_BACKEND="playwright"):
            run_render(render_job.pk)

        render_job.refresh_from_db()
        assert render_job.status == RenderStatus.SUCCESS
        assert render_job.engine == "playwright"
        with render_job.file.open("rb") as fh:
            data = fh.read()
        assert data.startswith(b"%PDF")
        assert len(data) > 1000  # a real A4 PDF, not a stub

    def test_png_render(self, db, agency, listing):
        from apps.rendering.services import run_render

        job = RenderJob.objects.create(
            agency=agency, listing=listing, kind="poster_png"
        )
        with override_settings(RENDER_BACKEND="playwright"):
            run_render(job.pk)

        job.refresh_from_db()
        assert job.status == RenderStatus.SUCCESS
        with job.file.open("rb") as fh:
            assert fh.read().startswith(b"\x89PNG")


# ─── Views ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRenderViews:
    def test_list_requires_login(self, client, listing):
        resp = client.get(f"/rendering/listings/{listing.pk}/jobs/")
        assert resp.status_code == 302

    def test_list_page_renders(self, client, user, listing, render_job):
        client.force_login(user)
        resp = client.get(f"/rendering/listings/{listing.pk}/jobs/")
        assert resp.status_code == 200
        assert b"render-job-%d" % render_job.pk in resp.content

    def test_create_htmx_returns_partial(self, client, user, listing):
        client.force_login(user)
        with patch("apps.rendering.tasks.render_poster_task.delay") as mock_delay:
            resp = client.post(
                f"/rendering/listings/{listing.pk}/jobs/create/",
                {"kind": "poster_pdf"},
                headers={"HX-Request": "true"},
            )
        assert resp.status_code == 201
        mock_delay.assert_called_once()
        assert b"render-job-" in resp.content

    def test_create_form_redirects_and_renders_eagerly(self, client, user, listing, settings):
        """Celery eager + stub backend → job is already success after POST."""
        settings.RENDER_BACKEND = "stub"
        client.force_login(user)
        resp = client.post(f"/rendering/listings/{listing.pk}/jobs/create/")
        assert resp.status_code == 302

        job = RenderJob.objects.get(listing=listing)
        assert job.status == RenderStatus.SUCCESS

    def test_create_other_agency_listing_404(self, client, user, agency_b):
        from apps.listings.models import DealType, Listing, PropertyType

        other = Listing.objects.create(
            agency=agency_b,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
            city="شهر",
        )
        client.force_login(user)
        resp = client.post(f"/rendering/listings/{other.pk}/jobs/create/")
        assert resp.status_code == 404

    def test_download_serves_file(self, client, user, render_job):
        from apps.rendering.services import run_render

        run_render(render_job.pk)
        client.force_login(user)
        resp = client.get(f"/rendering/jobs/{render_job.pk}/download/")
        assert resp.status_code == 200
        assert resp.streaming
        first_chunk = next(resp.streaming_content)
        assert first_chunk.startswith(b"%PDF")

    def test_download_without_file_404(self, client, user, render_job):
        client.force_login(user)
        resp = client.get(f"/rendering/jobs/{render_job.pk}/download/")
        assert resp.status_code == 404

    def test_download_other_agency_404(self, client, user_b, render_job):
        client.force_login(user_b)
        resp = client.get(f"/rendering/jobs/{render_job.pk}/download/")
        assert resp.status_code == 404

    def test_status_partial(self, client, user, render_job):
        client.force_login(user)
        resp = client.get(f"/rendering/jobs/{render_job.pk}/status/")
        assert resp.status_code == 200

    def test_status_other_agency_404(self, client, user_b, render_job):
        client.force_login(user_b)
        resp = client.get(f"/rendering/jobs/{render_job.pk}/status/")
        assert resp.status_code == 404
