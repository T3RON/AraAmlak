"""
Gemini draft-extraction provider — structured output via Interactions API.

Official docs read 2026-09 (constitution §10):
  https://ai.google.dev/gemini-api/docs/structured-output

Request:
  POST https://generativelanguage.googleapis.com/v1beta/interactions
  header: x-goog-api-key
  body:   {"model": ..., "input": "<prompt>",
           "response_format": {"type": "text",
                               "mime_type": "application/json",
                               "schema": {...}}}

Response: the JSON object itself arrives in `output_text`.

Official best practice: validate values in the application — this module
normalises aggressively (whitelist fields, coerce types, validate enums,
convert Jalali build years) before handing data to the service layer.
"""

from __future__ import annotations

import json
import logging

import requests

from .draft_base import DraftProvider

logger = logging.getLogger(__name__)

_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
_TIMEOUT = 60  # seconds

_PROMPT = (
    "این متن، رونویسی توضیحات یک مشاور املاک درباره یک فایل ملکی به زبان فارسی است.\n"
    "فقط اطلاعات واقعاً ذکرشده را استخراج کن؛ چیزی حدس نزن.\n"
    "قواعد:\n"
    "- قیمت‌ها را به عدد صحیح «تومان» تبدیل کن (میلیارد = 1e9، میلیون = 1e6).\n"
    "- «سال ساخت» را همان‌طور که گفته شده بده (شمسی مثل ۱۳۹۰ یا میلادی مثل 2011).\n"
    "- اگر آیتمی ذکر نشده، آن کلید را اصلاً برنگردان (برای boolean مقدار null بده).\n"
    "- property_type یکی از: apartment, villa, commercial, land, office, warehouse, other\n"
    "- deal_type یکی از: sale, rent, mortgage_rent\n"
    "- direction یکی از: north, south, east, west, north_east, north_west, south_east, south_west\n"
    "- district فقط نام محله است، بدون شهر.\n"
    "رونویسی:\n"
)


def _draft_schema() -> dict:
    """JSON Schema for the structured-output response_format."""
    enum = lambda *values: {"type": ["string", "null"], "enum": list(values)}  # noqa: E731
    integer = {"type": ["integer", "null"]}
    boolean = {"type": ["boolean", "null"]}
    string = {"type": ["string", "null"]}
    return {
        "type": "object",
        "properties": {
            "title": string,
            "property_type": enum(
                "apartment", "villa", "commercial", "land", "office", "warehouse", "other"
            ),
            "deal_type": enum("sale", "rent", "mortgage_rent"),
            "area": integer,
            "land_area": integer,
            "rooms": integer,
            "floor": integer,
            "total_floors": integer,
            "build_year": integer,
            "parking": boolean,
            "elevator": boolean,
            "storage": boolean,
            "balcony": boolean,
            "direction": enum(
                "north", "south", "east", "west",
                "north_east", "north_west", "south_east", "south_west",
            ),
            "sale_price": integer,
            "mortgage_amount": integer,
            "rent_amount": integer,
            "district": string,
        },
        "required": [],
    }


_INT_FIELDS = {
    "area",
    "land_area",
    "rooms",
    "floor",
    "total_floors",
    "build_year",
    "sale_price",
    "mortgage_amount",
    "rent_amount",
}
_BOOL_FIELDS = {"parking", "elevator", "storage", "balcony"}
_STR_FIELDS = {"title", "district"}
_ENUM_FIELDS = {
    "property_type": {
        "apartment", "villa", "commercial", "land", "office", "warehouse", "other"
    },
    "deal_type": {"sale", "rent", "mortgage_rent"},
    "direction": {
        "north", "south", "east", "west",
        "north_east", "north_west", "south_east", "south_west",
    },
}


def _normalize_build_year(year: int) -> int | None:
    """Jalali (1300–1499 or 2-digit) → Gregorian; pass Gregorian through."""
    if 1300 <= year <= 1499:
        return year + 621
    if 0 <= year <= 99:
        return year + 1300 + 621
    if 1900 <= year <= 2121:
        return year
    return None


def _normalize(raw: dict) -> dict:
    """Whitelist + type-coerce the model's JSON into draft data."""
    from apps.ai.draft_parser import ALLOWED_DRAFT_FIELDS

    data: dict = {}
    for key, value in (raw or {}).items():
        if key not in ALLOWED_DRAFT_FIELDS or value is None:
            continue
        if key in _INT_FIELDS:
            try:
                value = int(value)
            except (TypeError, ValueError):
                continue
            if key == "build_year":
                value = _normalize_build_year(value)
                if value is None:
                    continue
        elif key in _BOOL_FIELDS:
            value = bool(value)
        elif key in _STR_FIELDS:
            value = str(value).strip()
            if not value:
                continue
        elif key in _ENUM_FIELDS:
            value = str(value).strip()
            if value not in _ENUM_FIELDS[key]:
                continue
        data[key] = value

    # Sanity guards (mirrors Listing constraints)
    if data.get("area") is not None and data["area"] <= 0:
        del data["area"]
    if data.get("sale_price") is not None and data["sale_price"] < 0:
        del data["sale_price"]
    return data


class GeminiDraftProvider(DraftProvider):
    """
    Extracts listing fields with Gemini structured output.

    Performs an external HTTP call — route through Celery (is_async=True).
    """

    name = "gemini"
    is_async = True

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self._api_key = api_key
        self._model = model

    def extract(self, transcript: str) -> dict:
        from apps.ai.draft_parser import score_draft

        payload = {
            "model": self._model,
            "input": _PROMPT + (transcript or ""),
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": _draft_schema(),
            },
        }
        resp = requests.post(
            _URL,
            headers={
                "x-goog-api-key": self._api_key,
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json() or {}
        text = body.get("output_text")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Gemini draft response has no output_text")

        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Gemini draft response is not valid JSON: {exc}") from exc

        data = _normalize(raw if isinstance(raw, dict) else {})
        missing, confidence = score_draft(data)
        logger.info("[Gemini] draft extracted (%d fields, conf %.2f)", len(data), confidence)
        return {"data": data, "missing": missing, "confidence": confidence}
