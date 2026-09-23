"""
Listings search service — Phase 1D.

build_listing_queryset(agency, params) constructs a filtered, sorted queryset
from URL GET parameters. Works with SQLite (LIKE fallback) and PostgreSQL
(icontains / trigram on prod).

Supported GET params:
  q           — free-text (code / address / city / district / owner_name)
  deal_type   — sale | rent | mortgage_rent | pre_sale
  property_type — apartment | villa | commercial | land | office | warehouse | other
  status      — draft | active | reserved | sold | expired | archived
  city        — text filter on city field
  district    — text filter on district / محله
  min_area    — integer
  max_area    — integer
  min_price   — integer
  max_price   — integer
  min_rooms   — integer
  assigned_to — user pk
  sort        — created_at | -created_at | area | -area | price | -price
"""

from __future__ import annotations

from django.db.models import Q, QuerySet

from apps.core.text import normalize_fa
from apps.listings.models import Listing


def build_listing_queryset(params: dict) -> QuerySet:
    """
    Return a filtered + sorted Listing queryset (already agency-scoped via manager).
    Caller is responsible for calling .select_related(...) etc.
    """
    qs = Listing.objects.all()

    # ── free text ──────────────────────────────────────────────────────────
    q = normalize_fa(params.get("q", "")).strip()
    if q:
        qs = qs.filter(
            Q(code__icontains=q)
            | Q(city__icontains=q)
            | Q(district__icontains=q)
            | Q(address__icontains=q)
            | Q(title__icontains=q)
            | Q(owner_name__icontains=q)
        )

    # ── enum filters ───────────────────────────────────────────────────────
    if params.get("deal_type"):
        qs = qs.filter(deal_type=params["deal_type"])

    if params.get("property_type"):
        qs = qs.filter(property_type=params["property_type"])

    if params.get("status"):
        qs = qs.filter(status=params["status"])

    # ── location ───────────────────────────────────────────────────────────
    if params.get("city"):
        qs = qs.filter(city__icontains=normalize_fa(params["city"]))

    if params.get("district"):
        qs = qs.filter(district__icontains=normalize_fa(params["district"]))

    # ── numeric ranges ─────────────────────────────────────────────────────
    try:
        if params.get("min_area"):
            qs = qs.filter(area__gte=int(params["min_area"]))
        if params.get("max_area"):
            qs = qs.filter(area__lte=int(params["max_area"]))
        if params.get("min_rooms"):
            qs = qs.filter(rooms__gte=int(params["min_rooms"]))
    except (ValueError, TypeError):
        pass

    # Price: applies to sale_price OR rent_amount depending on deal_type
    try:
        if params.get("min_price"):
            p = int(params["min_price"])
            qs = qs.filter(
                Q(sale_price__gte=p) | Q(rent_amount__gte=p) | Q(mortgage_amount__gte=p)
            )
        if params.get("max_price"):
            p = int(params["max_price"])
            qs = qs.filter(
                Q(sale_price__lte=p) | Q(rent_amount__lte=p) | Q(mortgage_amount__lte=p)
            )
    except (ValueError, TypeError):
        pass

    # ── assignment ─────────────────────────────────────────────────────────
    if params.get("assigned_to"):
        try:
            qs = qs.filter(assigned_to_id=int(params["assigned_to"]))
        except (ValueError, TypeError):
            pass

    # ── sorting ────────────────────────────────────────────────────────────
    sort_map = {
        "created_at": "created_at",
        "-created_at": "-created_at",
        "area": "area",
        "-area": "-area",
        "price": "sale_price",
        "-price": "-sale_price",
    }
    sort = params.get("sort", "-created_at")
    order_by = sort_map.get(sort, "-created_at")
    qs = qs.order_by(order_by)

    return qs
