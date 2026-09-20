from django.contrib import admin

from apps.publishing.models import PortalConfig, PublishJob


@admin.register(PortalConfig)
class PortalConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "agency", "portal", "is_active", "created_at")
    list_filter = ("portal", "is_active", "agency")
    search_fields = ("agency__name",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("agency", "portal")


@admin.register(PublishJob)
class PublishJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "agency",
        "listing",
        "portal_config",
        "status",
        "external_id",
        "published_at",
        "retries",
        "created_at",
    )
    list_filter = ("status", "portal_config__portal", "agency")
    search_fields = ("listing__code", "external_id", "error_message")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "published_at")
