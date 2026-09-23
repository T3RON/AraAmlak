"""
Listings import service — Phase 1D.

Handles Excel (.xlsx) and CSV file parsing for bulk listing import.
Runs inside a Celery task.

Column mapping (case-insensitive, normalised):
  نوع معامله    → deal_type   (فروش=sale, اجاره=rent, رهن=mortgage_rent, پیش‌فروش=pre_sale)
  نوع ملک       → property_type (آپارتمان=apartment, ویلا=villa, تجاری=commercial, ...)
  شهر           → city
  محله          → district
  آدرس          → address
  متراژ         → area
  اتاق          → rooms
  طبقه          → floor
  کل طبقات      → total_floors
  سال ساخت      → build_year
  قیمت          → sale_price
  رهن           → mortgage_amount
  اجاره         → rent_amount
  پارکینگ       → parking (بله/خیر/true/false/1/0)
  آسانسور       → elevator
  انباری        → storage
  نام مالک      → owner_name
  توضیحات       → description

Deduplication: warn if a listing in the same agency has the same city+district+area
within ±5% (soft dedupe — does not block import, adds a warning to error_report).
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

from django.db import transaction

from apps.core.text import normalize_fa

logger = logging.getLogger(__name__)

# ─── Column header aliases ────────────────────────────────────────────────────

_DEAL_TYPE_MAP: dict[str, str] = {
    "فروش": "sale",
    "sale": "sale",
    "اجاره": "rent",
    "rent": "rent",
    "رهن و اجاره": "mortgage_rent",
    "رهن": "mortgage_rent",
    "mortgage_rent": "mortgage_rent",
    "mortgage": "mortgage_rent",
    "پیش فروش": "pre_sale",
    "پیش‌فروش": "pre_sale",
    "pre_sale": "pre_sale",
}

_PROPERTY_TYPE_MAP: dict[str, str] = {
    "آپارتمان": "apartment",
    "apartment": "apartment",
    "ویلا": "villa",
    "خانه": "villa",
    "ویلایی": "villa",
    "villa": "villa",
    "تجاری": "commercial",
    "مغازه": "commercial",
    "commercial": "commercial",
    "زمین": "land",
    "land": "land",
    "اداری": "office",
    "دفتر": "office",
    "office": "office",
    "انبار": "warehouse",
    "warehouse": "warehouse",
    "سایر": "other",
    "other": "other",
}

# Canonical column name → list of accepted aliases (all lowercased + normalised)
_COLUMN_ALIASES: dict[str, list[str]] = {
    "deal_type": ["نوع معامله", "معامله", "deal_type", "deal"],
    "property_type": ["نوع ملک", "نوع", "property_type", "property"],
    "city": ["شهر", "city"],
    "district": ["محله", "منطقه", "district", "neighborhood"],
    "address": ["آدرس", "address"],
    "area": ["متراژ", "area", "متراژ بنا"],
    "rooms": ["اتاق", "rooms", "تعداد اتاق"],
    "floor": ["طبقه", "floor"],
    "total_floors": ["کل طبقات", "total_floors", "تعداد طبقات"],
    "build_year": ["سال ساخت", "build_year", "year"],
    "sale_price": ["قیمت فروش", "قیمت", "sale_price", "price"],
    "mortgage_amount": ["رهن", "ودیعه", "mortgage_amount", "mortgage"],
    "rent_amount": ["اجاره", "اجاره ماهانه", "rent_amount", "rent"],
    "parking": ["پارکینگ", "parking"],
    "elevator": ["آسانسور", "elevator"],
    "storage": ["انباری", "storage"],
    "owner_name": ["نام مالک", "مالک", "owner_name", "owner"],
    "description": ["توضیحات", "description", "desc"],
}


def _build_alias_map() -> dict[str, str]:
    """Return {normalised_alias: canonical_name}."""
    result: dict[str, str] = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            result[normalize_fa(alias).lower()] = canonical
    return result


_ALIAS_MAP = _build_alias_map()


def _parse_bool(val: str) -> bool:
    v = normalize_fa(str(val)).strip().lower()
    return v in ("بله", "yes", "true", "1", "دارد", "✓", "✔")


def _parse_int(val: str) -> int | None:
    try:
        return int(normalize_fa(str(val)).strip())
    except (ValueError, TypeError):
        return None


def _map_headers(raw_headers: list[str]) -> dict[int, str]:
    """Map column index → canonical field name. Unknown columns are ignored."""
    mapping: dict[int, str] = {}
    for idx, header in enumerate(raw_headers):
        key = normalize_fa(str(header)).lower().strip()
        if key in _ALIAS_MAP:
            mapping[idx] = _ALIAS_MAP[key]
    return mapping


def _row_to_dict(row: list[str], col_map: dict[int, str]) -> dict[str, Any]:
    """Convert a raw row list to a dict of {canonical_field: value}."""
    result: dict[str, Any] = {}
    for idx, value in enumerate(row):
        if idx in col_map:
            result[col_map[idx]] = str(value).strip()
    return result


def _coerce_row(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """
    Coerce string values in *raw* to proper Python types.
    Returns (coerced_dict, list_of_error_messages).
    """
    data: dict[str, Any] = {}
    errors: list[str] = []

    # deal_type
    if "deal_type" in raw:
        v = normalize_fa(raw["deal_type"]).lower().strip()
        mapped = _DEAL_TYPE_MAP.get(v)
        if mapped:
            data["deal_type"] = mapped
        else:
            errors.append(f"نوع معامله نامعتبر: «{raw['deal_type']}»")

    # property_type
    if "property_type" in raw:
        v = normalize_fa(raw["property_type"]).lower().strip()
        mapped = _PROPERTY_TYPE_MAP.get(v)
        if mapped:
            data["property_type"] = mapped
        else:
            errors.append(f"نوع ملک نامعتبر: «{raw['property_type']}»")

    # Text fields
    for field in ("city", "district", "address", "owner_name", "description"):
        if raw.get(field):
            data[field] = normalize_fa(raw[field])

    # Integer fields
    for field in ("area", "rooms", "floor", "total_floors", "build_year"):
        if raw.get(field):
            v = _parse_int(raw[field])
            if v is not None:
                data[field] = v
            else:
                errors.append(f"مقدار عددی نامعتبر برای «{field}»: «{raw[field]}»")

    # BigInteger (prices)
    for field in ("sale_price", "mortgage_amount", "rent_amount"):
        if raw.get(field):
            v = _parse_int(raw[field])
            if v is not None and v > 0:
                data[field] = v
            elif raw[field].strip():
                errors.append(f"قیمت نامعتبر برای «{field}»: «{raw[field]}»")

    # Boolean fields
    for field in ("parking", "elevator", "storage"):
        if raw.get(field):
            data[field] = _parse_bool(raw[field])

    return data, errors


# ─── Dedupe check ─────────────────────────────────────────────────────────────


def check_duplicate(agency, city: str, district: str, area: int | None) -> bool:
    """
    Return True if a listing with same city + district + similar area
    already exists for this agency (soft dedupe warning — not a blocker).
    Tolerance: ±10% on area.
    """
    from apps.listings.models import Listing  # noqa: PLC0415

    qs = Listing.all_objects.filter(
        agency=agency,
        city__iexact=normalize_fa(city or ""),
    )
    if district:
        qs = qs.filter(district__iexact=normalize_fa(district))
    if area:
        lo = int(area * 0.90)
        hi = int(area * 1.10)
        qs = qs.filter(area__gte=lo, area__lte=hi)
    return qs.exists()


# ─── Excel / CSV parsing ──────────────────────────────────────────────────────


def _iter_xlsx(file_bytes: bytes):
    """Yield (headers, rows) from xlsx bytes. Requires openpyxl."""
    try:
        import openpyxl  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError("openpyxl is required for Excel import") from exc

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        return [], []
    headers = [str(c) if c is not None else "" for c in rows[0]]
    data_rows = [[str(c) if c is not None else "" for c in r] for r in rows[1:]]
    return headers, data_rows


def _iter_csv(file_bytes: bytes):
    """Yield (headers, rows) from csv bytes."""
    text = file_bytes.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []
    return rows[0], rows[1:]


def parse_import_file(
    file_bytes: bytes,
    filename: str,
) -> tuple[list[str], list[list[str]]]:
    """
    Auto-detect file type and return (headers, data_rows).
    Raises ValueError on unrecognised format.
    """
    name_lower = filename.lower()
    if name_lower.endswith(".xlsx") or name_lower.endswith(".xls"):
        return _iter_xlsx(file_bytes)
    if name_lower.endswith(".csv"):
        return _iter_csv(file_bytes)
    # Try magic bytes for xlsx (PK zip header)
    if file_bytes[:2] == b"PK":
        return _iter_xlsx(file_bytes)
    # Fall back to CSV
    return _iter_csv(file_bytes)


# ─── Main import runner ───────────────────────────────────────────────────────


def run_import_job(import_job_id: int) -> dict:
    """
    Main function called by Celery task.
    Reads the uploaded file, parses rows, creates Listing objects.
    Updates ImportJob status/counters.
    """
    from apps.listings.models import (  # noqa: PLC0415
        DealType,
        ImportJob,
        ImportJobStatus,
        Listing,
        ListingStatus,
        PropertyType,
    )

    try:
        job = ImportJob.all_objects.select_related("agency").get(pk=import_job_id)
    except ImportJob.DoesNotExist:
        logger.error("ImportJob %s not found", import_job_id)
        return {"error": "not_found"}

    ImportJob.all_objects.filter(pk=import_job_id).update(status=ImportJobStatus.PROCESSING)

    try:
        job.uploaded_file.open("rb")
        file_bytes = job.uploaded_file.read()
        job.uploaded_file.close()
    except Exception as exc:  # noqa: BLE001
        logger.exception("ImportJob %s: cannot read file: %s", import_job_id, exc)
        ImportJob.all_objects.filter(pk=import_job_id).update(
            status=ImportJobStatus.ERROR,
            error_report=[{"row": 0, "field": "file", "message": str(exc)}],
        )
        return {"error": "file_read_error"}

    filename = job.original_filename or "import.xlsx"
    try:
        headers, data_rows = parse_import_file(file_bytes, filename)
    except Exception as exc:  # noqa: BLE001
        logger.exception("ImportJob %s: parse error: %s", import_job_id, exc)
        ImportJob.all_objects.filter(pk=import_job_id).update(
            status=ImportJobStatus.ERROR,
            error_report=[{"row": 0, "field": "file", "message": f"خطای خواندن فایل: {exc}"}],
        )
        return {"error": "parse_error"}

    col_map = _map_headers(headers)
    total = len(data_rows)
    imported = 0
    error_count = 0
    error_report: list[dict] = []

    ImportJob.all_objects.filter(pk=import_job_id).update(total_rows=total)

    for row_idx, raw_row in enumerate(data_rows, start=2):
        raw = _row_to_dict(raw_row, col_map)
        if not any(raw.values()):
            continue  # skip blank rows

        data, row_errors = _coerce_row(raw)

        if row_errors:
            for msg in row_errors:
                error_report.append({"row": row_idx, "field": "", "message": msg})
            error_count += 1
            continue

        # Require at minimum deal_type + property_type + city
        missing = [f for f in ("deal_type", "property_type", "city") if f not in data]
        if missing:
            error_report.append({
                "row": row_idx,
                "field": ", ".join(missing),
                "message": f"فیلدهای اجباری خالی‌اند: {', '.join(missing)}",
            })
            error_count += 1
            continue

        # Validate enum values
        if data["deal_type"] not in [c.value for c in DealType]:
            error_report.append({
                "row": row_idx, "field": "deal_type",
                "message": f"نوع معامله نامعتبر: {data['deal_type']}",
            })
            error_count += 1
            continue

        if data["property_type"] not in [c.value for c in PropertyType]:
            error_report.append({
                "row": row_idx, "field": "property_type",
                "message": f"نوع ملک نامعتبر: {data['property_type']}",
            })
            error_count += 1
            continue

        # Soft dedupe warning (does not block)
        if check_duplicate(
            job.agency,
            data.get("city", ""),
            data.get("district", ""),
            data.get("area"),
        ):
            error_report.append({
                "row": row_idx,
                "field": "dedupe",
                "message": "⚠ احتمال تکراری بودن: فایل مشابه در همین آژانس وجود دارد",
            })

        try:
            with transaction.atomic():
                Listing.all_objects.create(
                    agency=job.agency,
                    status=ListingStatus.ACTIVE,
                    **data,
                )
            imported += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("ImportJob %s row %s error: %s", import_job_id, row_idx, exc)
            error_report.append({
                "row": row_idx, "field": "", "message": f"خطای DB: {exc}"
            })
            error_count += 1

    ImportJob.all_objects.filter(pk=import_job_id).update(
        status=ImportJobStatus.DONE,
        imported_rows=imported,
        error_rows=error_count,
        error_report=error_report,
    )

    logger.info(
        "ImportJob %s done: total=%s imported=%s errors=%s",
        import_job_id, total, imported, error_count,
    )
    return {
        "import_job_id": import_job_id,
        "total": total,
        "imported": imported,
        "errors": error_count,
    }
