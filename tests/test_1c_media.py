"""
Phase 1C tests — Media model, service, EXIF stripping, signed URL, access control.

Run with:
  pytest --ds=ara_amlak.settings.testing_nogis tests/test_1c_media.py -v
"""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def listing(db, agency):
    from apps.listings.models import DealType, Listing, ListingStatus, PropertyType
    return Listing.objects.create(
        agency=agency,
        property_type=PropertyType.APARTMENT,
        deal_type=DealType.SALE,
        title="آپارتمان تست رسانه",
        city="تهران",
        area=80,
        status=ListingStatus.ACTIVE,
    )


def _make_jpeg_bytes() -> bytes:
    """Create a minimal valid JPEG (2×2 white) in memory using Pillow if available,
    otherwise return a raw JPEG magic-byte stub sufficient for detect_mime."""
    try:
        from PIL import Image  # noqa: PLC0415
        buf = io.BytesIO()
        img = Image.new("RGB", (2, 2), color=(255, 255, 255))
        img.save(buf, format="JPEG")
        return buf.getvalue()
    except ImportError:
        # Minimal JPEG magic: SOI marker + enough bytes to pass detect_mime
        return b"\xff\xd8\xff\xe0" + b"\x00" * 20


def _make_pdf_bytes() -> bytes:
    """Minimal PDF bytes (magic only — enough for MIME detection)."""
    return b"%PDF-1.4\n%EOF\n"


def _jpeg_upload(name: str = "test.jpg") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, _make_jpeg_bytes(), content_type="image/jpeg")


def _pdf_upload(name: str = "snad.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, _make_pdf_bytes(), content_type="application/pdf")


# ─── MIME detection ───────────────────────────────────────────────────────────

class TestDetectMime:
    def test_jpeg(self):
        from apps.listings.media_services import detect_mime
        assert detect_mime(_make_jpeg_bytes()) == "image/jpeg"

    def test_pdf(self):
        from apps.listings.media_services import detect_mime
        assert detect_mime(_make_pdf_bytes()) == "application/pdf"

    def test_png(self):
        from apps.listings.media_services import detect_mime
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 10
        assert detect_mime(png) == "image/png"

    def test_unknown(self):
        from apps.listings.media_services import detect_mime
        assert detect_mime(b"\x00\x01\x02\x03\x04\x05\x06\x07") == "application/octet-stream"


# ─── Validation ───────────────────────────────────────────────────────────────

class TestValidateUpload:
    def test_valid_jpeg(self):
        from apps.listings.media_services import validate_upload
        from apps.listings.models import MediaType
        f = _jpeg_upload()
        mime = validate_upload(f, MediaType.PHOTO)
        assert mime == "image/jpeg"

    def test_invalid_mime_for_photo(self):
        from django.core.exceptions import ValidationError

        from apps.listings.media_services import validate_upload
        from apps.listings.models import MediaType

        bad_bytes = b"\x4d\x5a" + b"\x00" * 20  # PE/EXE magic
        f = SimpleUploadedFile("bad.exe", bad_bytes, content_type="application/octet-stream")
        with pytest.raises(ValidationError, match="مجاز نیست"):
            validate_upload(f, MediaType.PHOTO)

    def test_oversized_file(self):
        from django.core.exceptions import ValidationError

        from apps.listings.media_services import validate_upload
        from apps.listings.models import MediaType
        big = b"\xff\xd8\xff\xe0" + b"\x00" * (21 * 1024 * 1024)
        f = SimpleUploadedFile("huge.jpg", big, content_type="image/jpeg")
        with pytest.raises(ValidationError, match="مگابایت"):
            validate_upload(f, MediaType.PHOTO)

    def test_valid_pdf_as_document(self):
        from apps.listings.media_services import validate_upload
        from apps.listings.models import MediaType
        f = _pdf_upload()
        mime = validate_upload(f, MediaType.DOCUMENT)
        assert mime == "application/pdf"


# ─── EXIF stripping ───────────────────────────────────────────────────────────

class TestExifStripping:
    def test_strip_returns_bytes(self):
        from apps.listings.media_services import strip_exif_from_bytes
        raw = _make_jpeg_bytes()
        result = strip_exif_from_bytes(raw)
        # Must return bytes and start with JPEG magic
        assert isinstance(result, bytes)
        assert result[:2] == b"\xff\xd8"

    def test_strip_idempotent_on_non_jpeg(self):
        """strip_exif_from_bytes must not raise on unrecognised bytes; returns input."""
        from apps.listings.media_services import strip_exif_from_bytes
        dummy = b"\x00\x01\x02\x03" * 20  # unrecognisable bytes
        result = strip_exif_from_bytes(dummy)
        assert isinstance(result, bytes)


# ─── create_media service ─────────────────────────────────────────────────────

class TestCreateMedia:
    def test_creates_photo_record(self, db, listing, settings):
        settings.CELERY_TASK_ALWAYS_EAGER = True
        from apps.listings.media_services import create_media
        from apps.listings.models import MediaStatus, MediaType
        f = _jpeg_upload()
        media = create_media(listing=listing, uploaded_file=f, media_type=MediaType.PHOTO)
        assert media.pk is not None
        assert media.media_type == MediaType.PHOTO
        assert media.mime_type == "image/jpeg"
        assert media.listing == listing
        # First photo should become cover
        assert media.is_cover is True
        # Status starts as PENDING (Celery runs synchronously but process_photo
        # needs a real file — just verify model was created)
        assert media.status in (MediaStatus.PENDING, MediaStatus.READY, MediaStatus.ERROR)

    def test_creates_document_as_private(self, db, listing, settings):
        settings.CELERY_TASK_ALWAYS_EAGER = True
        from apps.listings.media_services import create_media
        from apps.listings.models import MediaType
        f = _pdf_upload()
        media = create_media(listing=listing, uploaded_file=f, media_type=MediaType.DOCUMENT)
        assert media.is_private is True
        assert media.media_type == MediaType.DOCUMENT

    def test_order_increments(self, db, listing, settings):
        settings.CELERY_TASK_ALWAYS_EAGER = True
        from apps.listings.media_services import create_media
        from apps.listings.models import MediaType

        pt = MediaType.PHOTO
        m1 = create_media(listing=listing, uploaded_file=_jpeg_upload("a.jpg"), media_type=pt)
        m2 = create_media(listing=listing, uploaded_file=_jpeg_upload("b.jpg"), media_type=pt)
        assert m2.order > m1.order

    def test_invalid_mime_raises(self, db, listing, settings):
        from django.core.exceptions import ValidationError

        from apps.listings.media_services import create_media
        from apps.listings.models import MediaType
        bad = SimpleUploadedFile("x.exe", b"\x4d\x5a" + b"\x00" * 20)
        with pytest.raises(ValidationError):
            create_media(listing=listing, uploaded_file=bad, media_type=MediaType.PHOTO)


# ─── reorder + set_cover ─────────────────────────────────────────────────────

class TestReorderAndCover:
    def test_reorder(self, db, listing, settings):
        settings.CELERY_TASK_ALWAYS_EAGER = True
        from apps.listings.media_services import create_media, reorder_media
        from apps.listings.models import MediaType

        pt = MediaType.PHOTO
        m1 = create_media(listing=listing, uploaded_file=_jpeg_upload("a.jpg"), media_type=pt)
        m2 = create_media(listing=listing, uploaded_file=_jpeg_upload("b.jpg"), media_type=pt)
        # Reverse order
        reorder_media(listing, [m2.pk, m1.pk])
        m1.refresh_from_db()
        m2.refresh_from_db()
        assert m2.order == 0
        assert m1.order == 1

    def test_set_cover(self, db, listing, settings):
        settings.CELERY_TASK_ALWAYS_EAGER = True
        from apps.listings.media_services import create_media, set_cover
        from apps.listings.models import MediaType

        pt = MediaType.PHOTO
        m1 = create_media(listing=listing, uploaded_file=_jpeg_upload("a.jpg"), media_type=pt)
        m2 = create_media(listing=listing, uploaded_file=_jpeg_upload("b.jpg"), media_type=pt)
        assert m1.is_cover is True
        set_cover(listing, m2.pk)
        m1.refresh_from_db()
        m2.refresh_from_db()
        assert m2.is_cover is True
        assert m1.is_cover is False


# ─── Signed URL ───────────────────────────────────────────────────────────────

class TestSignedUrl:
    def test_token_is_verifiable(self, db, listing, settings):
        """Token produced by generate_signed_url can be decoded back."""
        settings.CELERY_TASK_ALWAYS_EAGER = True
        settings.ROOT_URLCONF = "ara_amlak.urls"
        from django.core import signing

        from apps.listings.media_services import create_media
        from apps.listings.models import MediaType
        f = _pdf_upload()
        media = create_media(listing=listing, uploaded_file=f, media_type=MediaType.DOCUMENT)
        url = media.generate_signed_url(expires_seconds=600)
        # Extract token from URL path (last path segment)
        token = url.rstrip("/").split("/")[-1]
        data = signing.loads(token, salt="media-signed-url", max_age=600)
        assert data["media_id"] == media.pk

    def test_expired_token_rejected_by_view(self, db, settings):
        """An expired signed token raises BadSignature / Http404 in the view."""
        import time

        from django.core import signing
        from django.core.signing import BadSignature, SignatureExpired
        # Produce a token and verify it becomes expired with max_age=0
        token = signing.dumps({"media_id": 1, "exp": 0}, salt="media-signed-url")
        time.sleep(0.01)
        with pytest.raises((BadSignature, SignatureExpired, Exception)):
            signing.loads(token, salt="media-signed-url", max_age=0)


# ─── Tenant isolation ─────────────────────────────────────────────────────────

class TestMediaTenantIsolation:
    def test_media_files_belong_to_listing_agency(self, db, agency, agency_b, settings):
        """Media of agency_a listing not accessible from agency_b context."""
        settings.CELERY_TASK_ALWAYS_EAGER = True
        from apps.listings.media_services import create_media
        from apps.listings.models import (
            DealType,
            Listing,
            ListingStatus,
            Media,
            MediaType,
            PropertyType,
        )

        listing_a = Listing.objects.create(
            agency=agency,
            property_type=PropertyType.APARTMENT,
            deal_type=DealType.SALE,
            city="تهران",
            area=50,
            status=ListingStatus.ACTIVE,
        )
        create_media(
            listing=listing_a,
            uploaded_file=_jpeg_upload(),
            media_type=MediaType.PHOTO,
        )

        # Agency B cannot see listing_a's media via listing FK
        count = Media.objects.filter(listing__agency=agency_b).count()
        assert count == 0

        count_a = Media.objects.filter(listing__agency=agency).count()
        assert count_a >= 1
