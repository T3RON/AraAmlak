"""
Listings Django admin.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.listings.models import Listing, ListingImage


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 0
    fields = ("image", "order", "is_cover", "uploaded_at")
    readonly_fields = ("uploaded_at",)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "agency",
        "property_type",
        "deal_type",
        "city",
        "area",
        "status",
        "created_at",
    )
    list_filter = ("status", "property_type", "deal_type", "agency")
    search_fields = ("code", "title", "city", "owner_name")
    readonly_fields = ("code", "created_at", "updated_at")
    inlines = [ListingImageInline]
    fieldsets = (
        (_("شناسه"), {"fields": ("agency", "code", "title", "status", "branch", "assigned_to")}),
        (_("نوع"), {"fields": ("property_type", "deal_type")}),
        (_("موقعیت"), {"fields": ("province", "city", "district", "address")}),
        (_("مشخصات فیزیکی"), {"fields": (
            "area", "rooms", "floor", "total_floors",
            "build_year", "parking", "elevator", "storage", "direction",
        )}),
        (_("قیمت"), {"fields": (
            "sale_price", "mortgage_amount", "rent_amount", "price_negotiable",
        )}),
        (_("مالک (محرمانه)"), {"fields": ("owner_name", "owner_phone"), "classes": ("collapse",)}),
        (_("تاریخ‌ها"), {"fields": ("published_at", "expires_at", "created_at", "updated_at")}),
    )
