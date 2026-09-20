"""
CRM Django admin.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.crm.models import Request


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = (
        "client_name",
        "agency",
        "deal_type",
        "city",
        "status",
        "priority",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "deal_type", "priority", "source", "agency")
    search_fields = ("client_name", "city", "notes")
    readonly_fields = ("created_at", "updated_at", "closed_at")
    fieldsets = (
        (_("مراجعه‌کننده"), {"fields": ("agency", "client_name", "client_phone", "source")}),
        (_("نیاز"), {"fields": (
            "deal_type", "property_types",
            "min_area", "max_area", "min_rooms", "max_rooms",
            "city", "district", "min_budget", "max_budget", "notes",
        )}),
        (_("وضعیت"), {"fields": ("status", "priority", "assigned_to")}),
        (_("تاریخ‌ها"), {"fields": ("contacted_at", "closed_at", "created_at", "updated_at")}),
    )
