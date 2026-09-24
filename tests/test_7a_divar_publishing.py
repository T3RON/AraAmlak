"""
Tests for Phase 7A — Real Divar (Kenar) publishing adapter.

All HTTP is mocked — no real network calls.
Coverage:
- get_adapter registry (divar registered, unknown raises)
- config validation (missing api key / category_slug → PublishError)
- title/description composition
- category_fields {{field}} substitution
- image upload flow (upload-urls GET → PUT binary → images list)
- submit success (post_token → external_id) + payload shape + headers
- submit failures (HTTP error, missing post_token)
- service end-to-end: publish_listing with Divar config → job success/failed
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.publishing.adapters import (
    ADAPTER_MAP,
    DivarAdapter,
    DummyAdapter,
    PublishError,
    get_adapter,
)
from apps.publishing.models import JobStatus, Portal, PortalConfig

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def listing(db, agency):
    from apps.listings.models import DealType, Listing, PropertyType

    return Listing.objects.create(
        agency=agency,
        property_type=PropertyType.APARTMENT,
        deal_type=DealType.SALE,
        title="آپارتمان نوساز سعادت‌آباد",
        city="تهران",
        district="سعادت‌آباد",
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
def divar_config(db, agency):
    return PortalConfig.objects.create(
        agency=agency,
        portal=Portal.DIVAR,
        credentials="kenar-api-key-123",
        extra_config={
            "category_slug": "apartment-sell",
            "category_fields": {
                "price": "{{sale_price}}",
                "meter": "{{area}}",
                "room_count": "{{rooms}}",
                "static_key": "static-value",
            },
        },
    )


def _adapter() -> DivarAdapter:
    adapter = get_adapter("divar")
    assert isinstance(adapter, DivarAdapter)
    return adapter


def _mock_resp(json_data=None, status=200, text=""):
    resp = MagicMock()
    resp.ok = status < 400
    resp.status_code = status
    resp.text = text
    resp.json.return_value = json_data if json_data is not None else {}
    if status >= 400:
        resp.raise_for_status.side_effect = RuntimeError(f"HTTP {status}")
    else:
        resp.raise_for_status = lambda: None
    return resp


# ─── Registry ─────────────────────────────────────────────────────────────────


class TestRegistry:
    def test_divar_registered(self):
        assert get_adapter("divar").__class__ is DivarAdapter

    def test_dummy_still_works(self):
        assert isinstance(get_adapter("dummy"), DummyAdapter)

    def test_unknown_portal_raises(self):
        with pytest.raises(PublishError):
            get_adapter("nonexistent_portal")

    def test_map_has_no_sheypoor(self):
        """Sheypoor has no documented public API — must stay unregistered."""
        assert "sheypoor" not in ADAPTER_MAP


# ─── Config validation ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestConfigValidation:
    def test_missing_api_key(self, listing, divar_config):
        divar_config.credentials = ""
        divar_config.save()
        with pytest.raises(PublishError, match="کلید API"):
            _adapter().publish(listing, divar_config)

    def test_missing_category_slug(self, listing, divar_config):
        divar_config.extra_config = {}
        divar_config.save()
        with pytest.raises(PublishError, match="category_slug"):
            _adapter().publish(listing, divar_config)


# ─── Content composition ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestContent:
    def test_title(self, listing):
        title = DivarAdapter()._build_title(listing)
        assert "فروش" in title and "آپارتمان" in title
        assert "۸۰ متری" in title and "تهران" in title

    def test_title_rent_verb(self, listing):
        listing.deal_type = "rent"
        assert "اجاره" in DivarAdapter()._build_title(listing)

    def test_description_contains_specs_and_price(self, listing):
        desc = DivarAdapter()._build_description(listing)
        assert "آپارتمان نوساز سعادت‌آباد" in desc
        assert "۸۰ متر" in desc and "۲ خواب" in desc
        assert "طبقه ۳" in desc
        assert "پارکینگ" in desc and "آسانسور" in desc
        assert "۲ میلیارد و ۷۰۰ میلیون تومان" in desc

    def test_category_fields_substitution(self, listing, divar_config):
        fields = DivarAdapter()._build_category_fields(listing, divar_config.extra_config)
        assert fields["price"] == 2_700_000_000
        assert fields["meter"] == 80
        assert fields["room_count"] == 2
        assert fields["static_key"] == "static-value"  # non-template passthrough

    def test_category_fields_skips_missing_values(self, listing, divar_config):
        divar_config.extra_config["category_fields"]["rent_amount"] = "{{rent_amount}}"
        fields = DivarAdapter()._build_category_fields(listing, divar_config.extra_config)
        assert "rent_amount" not in fields


# ─── Image upload flow ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestImageUpload:
    def _make_photo(self, listing, name="photo.jpg"):
        from apps.listings.models import Media, MediaType

        jpeg = SimpleUploadedFile(name, b"\xff\xd8\xff\xe0" + b"\x00" * 20)
        return Media.objects.create(
            listing=listing,
            media_type=MediaType.PHOTO,
            file=jpeg,
            is_cover=True,
            mime_type="image/jpeg",
        )

    def test_upload_flow_returns_urls(self, listing, divar_config):
        photo = self._make_photo(listing)
        adapter = _adapter()

        upload_resp = _mock_resp(
            {"image": {"http_method": "PUT", "url": "https://upload.divar.ir/img/1"}}
        )
        put_resp = _mock_resp({})

        with (
            patch("requests.get", return_value=upload_resp) as mock_get,
            patch("requests.put", return_value=put_resp) as mock_put,
        ):
            urls = adapter._upload_images(listing, "kenar-api-key-123", {})

        assert urls == ["https://upload.divar.ir/img/1"]
        _, get_kwargs = mock_get.call_args
        assert get_kwargs["headers"]["X-API-Key"] == "kenar-api-key-123"
        assert "upload-urls" in mock_get.call_args[0][0]
        _, put_kwargs = mock_put.call_args
        assert put_kwargs["data"].startswith(b"\xff\xd8")  # raw JPEG bytes
        assert photo.pk  # referenced media used

    def test_upload_failure_continues_without_images(self, listing, divar_config):
        self._make_photo(listing)
        adapter = _adapter()

        with patch("requests.get", side_effect=RuntimeError("network down")):
            urls = adapter._upload_images(listing, "kenar-api-key-123", {})

        assert urls == []  # text-only ad, no crash

    def test_no_photos_means_empty_images(self, listing, divar_config):
        urls = _adapter()._upload_images(listing, "kenar-api-key-123", {})
        assert urls == []


# ─── Submit ───────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSubmit:
    def test_success_returns_token(self, listing, divar_config):
        adapter = _adapter()

        submit_resp = _mock_resp({"post_token": "abc-token-99"})
        with (
            patch("requests.get", return_value=_mock_resp({"image": None})),
            patch("requests.post", return_value=submit_resp) as mock_post,
        ):
            result = adapter.publish(listing, divar_config)

        assert result == {"external_id": "abc-token-99"}
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["X-API-Key"] == "kenar-api-key-123"
        assert "posts/new-v2" in mock_post.call_args[0][0]

        payload = kwargs["json"]
        gd = payload["general_data"]
        assert gd["title"].startswith("فروش آپارتمان")
        assert gd["city"] == "تهران"
        assert gd["category_slug"] == "apartment-sell"
        assert gd["chat_enabled"] is True
        assert gd["hide_phone"] is False
        assert gd["location_type"] == "LOCATION_TYPE_APPROXIMATE"
        assert gd["district"] == "سعادت‌آباد"
        assert payload["category_fields"]["price"] == 2_700_000_000

    def test_http_error_raises(self, listing, divar_config):
        adapter = _adapter()
        with (
            patch("requests.get", return_value=_mock_resp({"image": None})),
            patch("requests.post", return_value=_mock_resp({}, status=403, text="forbidden")),
        ):
            with pytest.raises(PublishError, match="403"):
                adapter.publish(listing, divar_config)

    def test_missing_post_token_raises(self, listing, divar_config):
        adapter = _adapter()
        with (
            patch("requests.get", return_value=_mock_resp({"image": None})),
            patch("requests.post", return_value=_mock_resp({"unexpected": 1})),
        ):
            with pytest.raises(PublishError, match="post_token"):
                adapter.publish(listing, divar_config)


# ─── Service end-to-end ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPublishListingService:
    def test_divar_publish_success(self, listing, divar_config):
        from apps.publishing.services import publish_listing

        with (
            patch("requests.get", return_value=_mock_resp({"image": None})),
            patch(
                "requests.post", return_value=_mock_resp({"post_token": "token-e2e"})
            ),
        ):
            job = publish_listing(listing.pk, divar_config.pk)

        assert job.status == JobStatus.SUCCESS
        assert job.external_id == "token-e2e"
        assert job.published_at is not None

    def test_divar_publish_failure_marks_failed(self, listing, divar_config):
        from apps.publishing.services import publish_listing

        with (
            patch("requests.get", return_value=_mock_resp({"image": None})),
            patch(
                "requests.post",
                return_value=_mock_resp({}, status=400, text="bad category"),
            ),
        ):
            job = publish_listing(listing.pk, divar_config.pk)

        assert job.status == JobStatus.FAILED
        assert "400" in job.error_message
