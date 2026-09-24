"""
Publishing adapters — adapter pattern for portal integrations.

Each portal has its own adapter class.
The DummyAdapter is used for testing and local development.

To add a new portal:
1. Create a new class inheriting BasePortalAdapter
2. Override publish()
3. Register in ADAPTER_MAP

Note: Real portal adapters (Divar, Sheypoor) require official API credentials.
Per project constitution, never guess API endpoints — read official docs first.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.listings.models import Listing
    from apps.publishing.models import PortalConfig


# ─── Exceptions ───────────────────────────────────────────────────────────────


class PublishError(Exception):
    """Raised when a portal adapter fails to publish a listing."""


# ─── Base adapter ─────────────────────────────────────────────────────────────


class BasePortalAdapter:
    """
    Abstract base class for all portal adapters.

    Subclasses must implement `publish()`.
    `publish()` should return a dict with at least {"external_id": str}.
    On failure, raise PublishError with a descriptive message.
    """

    def publish(self, listing: Listing, config: PortalConfig) -> dict:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement publish()"
        )


# ─── Dummy adapter (testing / local dev) ──────────────────────────────────────


class DummyAdapter(BasePortalAdapter):
    """
    Always succeeds with a fake external_id.
    Used for development, testing, and demo environments.
    """

    def publish(self, listing: Listing, config: PortalConfig) -> dict:
        return {"external_id": f"dummy-{listing.pk}"}


# ─── Divar adapter (real — Kenar open platform) ───────────────────────────────


class DivarAdapter(BasePortalAdapter):
    """
    Real adapter for Divar (دیوار) via the official Kenar open platform.

    Official docs read 2026-09 (constitution §10):
      - https://divar-ir.github.io/kenar-docs
      - https://github.com/divar-ir/kenar-sdk-python (PostApi / AssetsApi)

    Endpoints (base: https://open-api.divar.ir), auth header X-API-Key:
      1. GET  /v2/open-platform/post/upload-urls
             → {"image": {"http_method", "url"}, ...}
      2. upload image binary to that url (POST/PUT per http_method, api-key)
      3. POST /experimental/open-platform/posts/new-v2
             body: {"general_data": {...}, "category_fields": {...}}
             → {"post_token": "..."}

    PortalConfig usage:
      credentials    — Kenar API key (X-API-Key), encrypted at rest
      extra_config   — {
            "category_slug":   required, e.g. "apartment-sell" (no guessing:
                               see kenar submit-schema docs),
            "category_fields": {"price": "{{sale_price}}", ...} — values may
                               reference Listing fields via {{field}};
            "chat_enabled": true, "hide_phone": false,
            "location_type": "LOCATION_TYPE_APPROXIMATE",
            "max_images": 3,
        }
    """

    _BASE = "https://open-api.divar.ir"
    _UPLOAD_URLS_PATH = "/v2/open-platform/post/upload-urls"
    _SUBMIT_PATH = "/experimental/open-platform/posts/new-v2"
    _TIMEOUT = 30

    _DEAL_VERBS = {"sale": "فروش", "rent": "اجاره", "mortgage_rent": "رهن و اجاره"}

    def publish(self, listing: Listing, config: PortalConfig) -> dict:

        api_key = (config.credentials or "").strip()
        if not api_key:
            raise PublishError(
                "کلید API کنار (دیوار) در تنظیمات پورتال ثبت نشده است."
            )
        extra = config.extra_config or {}
        category_slug = extra.get("category_slug")
        if not category_slug:
            raise PublishError(
                "category_slug در extra_config پورتال تنظیم نشده است "
                "(فهرست دسته‌ها در مستندات کنار)."
            )

        images = self._upload_images(listing, api_key, extra)
        payload = {
            "general_data": {
                "title": self._build_title(listing),
                "description": self._build_description(listing),
                "city": listing.city,
                "category_slug": category_slug,
                "chat_enabled": bool(extra.get("chat_enabled", True)),
                "hide_phone": bool(extra.get("hide_phone", False)),
                "images": images,
                "location_type": extra.get(
                    "location_type", "LOCATION_TYPE_APPROXIMATE"
                ),
            },
            "category_fields": self._build_category_fields(listing, extra),
        }
        if listing.district:
            payload["general_data"]["district"] = listing.district

        token = self._submit(payload, api_key)
        return {"external_id": token}

    # ── Content composition ───────────────────────────────────────────────

    def _build_title(self, listing: Listing) -> str:
        from apps.core.currency import to_persian_digits

        verb = self._DEAL_VERBS.get(listing.deal_type, "فروش")
        kind = listing.get_property_type_display()
        title = f"{verb} {kind}"
        if listing.area:
            title += f" {to_persian_digits(listing.area)} متری"
        if listing.city:
            title += f"، {listing.city}"
        return title[:120]  # API field limit guard

    def _build_description(self, listing: Listing) -> str:
        from apps.core.currency import format_number_fa, format_toman

        lines: list[str] = []
        if listing.title:
            lines.append(listing.title)
        specs = []
        if listing.area:
            specs.append(f"{format_number_fa(listing.area)} متر")
        if listing.rooms:
            specs.append(f"{format_number_fa(listing.rooms)} خواب")
        if listing.floor is not None:
            specs.append(f"طبقه {format_number_fa(listing.floor)}")
        if listing.total_floors:
            specs.append(f"از {format_number_fa(listing.total_floors)} طبقه")
        if listing.build_year:
            specs.append(f"ساخت {format_number_fa(listing.build_year)}")
        if specs:
            lines.append("، ".join(specs))

        amenities = [
            label
            for flag, label in (
                (listing.parking, "پارکینگ"),
                (listing.elevator, "آسانسور"),
                (listing.storage, "انباری"),
                (listing.balcony, "بالکن"),
            )
            if flag
        ]
        if amenities:
            lines.append("امکانات: " + "، ".join(amenities))

        prices = []
        if listing.sale_price:
            prices.append(format_toman(listing.sale_price))
        if listing.mortgage_amount:
            prices.append("رهن " + format_toman(listing.mortgage_amount))
        if listing.rent_amount:
            prices.append("اجاره " + format_toman(listing.rent_amount))
        if prices:
            lines.append("قیمت: " + " — ".join(prices))

        agency = getattr(listing.agency, "name", "")
        phone = getattr(listing.agency, "phone", "")
        contact = " ".join(x for x in (agency, phone) if x)
        if contact:
            lines.append(f"کارگزاری {contact}")
        return "\n".join(lines)

    def _build_category_fields(
        self, listing: Listing, extra: dict
    ) -> dict:
        """Fill extra_config['category_fields'] values referencing {{field}}."""

        template_fields = extra.get("category_fields") or {}
        listing_values = {
            field: getattr(listing, field, None)
            for field in (
                "sale_price",
                "rent_amount",
                "mortgage_amount",
                "area",
                "land_area",
                "rooms",
                "floor",
                "total_floors",
                "build_year",
                "city",
                "district",
            )
        }
        result = {}
        for key, template in template_fields.items():
            if isinstance(template, str) and "{{" in template:
                ref = template.strip("{}").strip()
                result[key] = listing_values.get(ref)
            else:
                result[key] = template
        return {k: v for k, v in result.items() if v is not None}

    # ── HTTP steps ────────────────────────────────────────────────────────

    def _headers(self, api_key: str) -> dict:
        return {"X-API-Key": api_key}

    def _upload_images(self, listing: Listing, api_key: str, extra: dict) -> list[str]:
        """
        Upload up to max_images cover-ordered photos.

        Returns the uploaded image URLs. Failures are logged and skipped —
        a text-only ad is better than a failed publish.
        """
        import logging  # noqa: PLC0415

        import requests  # noqa: PLC0415

        logger = logging.getLogger(__name__)
        max_images = int(extra.get("max_images", 3))
        photos = (
            listing.media_files.filter(media_type="photo", is_private=False)
            .order_by("-is_cover", "order", "created_at")[:max_images]
        )

        urls: list[str] = []
        for photo in photos:
            try:
                upload = requests.get(
                    f"{self._BASE}{self._UPLOAD_URLS_PATH}",
                    headers=self._headers(api_key),
                    timeout=self._TIMEOUT,
                )
                upload.raise_for_status()
                image_info = (upload.json() or {}).get("image") or {}
                url = image_info.get("url")
                if not url:
                    raise PublishError("پاسخ upload-urls فاقد image.url است")
                method = (image_info.get("http_method") or "PUT").upper()
                with photo.file.open("rb") as fh:
                    data = fh.read()
                if method == "POST":
                    requests.post(
                        url, data=data, headers=self._headers(api_key), timeout=self._TIMEOUT
                    ).raise_for_status()
                else:
                    requests.put(
                        url, data=data, headers=self._headers(api_key), timeout=self._TIMEOUT
                    ).raise_for_status()
                urls.append(url)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "DivarAdapter: image upload failed for media #%s: %s",
                    photo.pk,
                    exc,
                )
        return urls

    def _submit(self, payload: dict, api_key: str) -> str:
        import requests  # noqa: PLC0415

        resp = requests.post(
            f"{self._BASE}{self._SUBMIT_PATH}",
            json=payload,
            headers={**self._headers(api_key), "Content-Type": "application/json"},
            timeout=self._TIMEOUT,
        )
        if not resp.ok:
            raise PublishError(
                f"Divar submit failed ({resp.status_code}): {resp.text[:300]}"
            )
        data = resp.json() or {}
        token = data.get("post_token")
        if not token:
            raise PublishError(
                f"Divar submit response has no post_token: {str(data)[:300]}"
            )
        return token


# ─── Registry ─────────────────────────────────────────────────────────────────

ADAPTER_MAP: dict[str, type[BasePortalAdapter]] = {
    "dummy": DummyAdapter,
    "divar": DivarAdapter,
    # "sheypoor": — no documented public API; do not guess endpoints (§10)
}


def get_adapter(portal: str) -> BasePortalAdapter:
    """Return an instantiated adapter for the given portal key."""
    cls = ADAPTER_MAP.get(portal)
    if cls is None:
        raise PublishError(f"No adapter registered for portal: {portal!r}")
    return cls()
