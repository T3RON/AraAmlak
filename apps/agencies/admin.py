"""Agencies admin configuration."""

from django.contrib import admin

from .models import Agency, AgencyMember, Branch

# Use GISModelAdmin only when GDAL is available
try:
    from django.contrib.gis.admin import GISModelAdmin as BranchBaseAdmin
except Exception:  # noqa: BLE001
    BranchBaseAdmin = admin.ModelAdmin  # type: ignore[assignment,misc]


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "plan", "is_active", "created_at"]
    list_filter = ["plan", "is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Branch)
class BranchAdmin(BranchBaseAdmin):
    list_display = ["name", "agency", "phone", "is_active"]
    list_filter = ["agency", "is_active"]
    search_fields = ["name", "address"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(AgencyMember)
class AgencyMemberAdmin(admin.ModelAdmin):
    list_display = ["user", "agency", "role", "joined_at"]
    list_filter = ["agency", "role"]
    search_fields = ["user__phone", "user__full_name"]
    readonly_fields = ["joined_at", "created_at", "updated_at"]
