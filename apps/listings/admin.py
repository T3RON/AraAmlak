"""
Listings Django admin.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.listings.models import (
    City,
    Feature,
    Listing,
    ListingImage,
    ListingStatusHistory,
    Neighborhood,
    NeighborhoodAdjacency,
)

# ─── Geo taxonomy ─────────────────────────────────────────────────────────────


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "province", "slug"]
    list_filter = ["province"]
    search_fields = ["name", "province"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["province", "name"]


class NeighborhoodInline(admin.TabularInline):
    model = Neighborhood
    extra = 0
    fields = ["name", "aliases"]


@admin.register(Neighborhood)
class NeighborhoodAdmin(admin.ModelAdmin):
    list_display = ["name", "city"]
    list_filter = ["city__province", "city"]
    search_fields = ["name", "aliases", "city__name"]
    ordering = ["city", "name"]


@admin.register(NeighborhoodAdjacency)
class NeighborhoodAdjacencyAdmin(admin.ModelAdmin):
    list_display = ["from_neighborhood", "to_neighborhood"]
    search_fields = [
        "from_neighborhood__name",
        "to_neighborhood__name",
    ]


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ["name", "icon"]
    search_fields = ["name"]


# ─── Listing ──────────────────────────────────────────────────────────────────


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 0
    fields = ("image", "caption", "order", "is_cover", "uploaded_at")
    readonly_fields = ("uploaded_at",)


class ListingStatusHistoryInline(admin.TabularInline):
    model = ListingStatusHistory
    extra = 0
    fields = ("old_status", "new_status", "changed_by", "note", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "code", "agency", "property_type", "deal_type",
        "city", "area", "status", "created_at",
    )
    list_filter = ("status", "property_type", "deal_type", "agency")
    search_fields = ("code", "title", "city", "owner_name")
    readonly_fields = ("code", "created_at", "updated_at")
    filter_horizontal = ("features",)
    inlines = [ListingImageInline, ListingStatusHistoryInline]
    fieldsets = (
        (_("شناسه"), {
            "fields": ("agency", "code", "title", "status", "branch", "assigned_to"),
        }),
        (_("نوع"), {"fields": ("property_type", "deal_type")}),
        (_("موقعیت"), {
            "fields": ("neighborhood", "province", "city", "district", "address"),
        }),
        (_("مشخصات فیزیکی"), {"fields": (
            "area", "land_area", "rooms", "floor", "total_floors",
            "units_per_floor", "build_year",
            "parking", "elevator", "storage", "balcony", "direction",
            "features",
        )}),
        (_("قیمت"), {
            "fields": ("sale_price", "mortgage_amount", "rent_amount", "price_negotiable"),
        }),
        (_("مالک (محرمانه)"), {
            "fields": ("owner_name", "owner_phone"),
            "classes": ("collapse",),
        }),
        (_("تاریخ‌ها"), {
            "fields": ("published_at", "expires_at", "created_at", "updated_at"),
        }),
    )
