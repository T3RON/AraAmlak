"""Admin for the rendering app."""

from django.contrib import admin

from .models import RenderJob


@admin.register(RenderJob)
class RenderJobAdmin(admin.ModelAdmin):
    list_display = ["pk", "agency", "listing", "kind", "status", "engine", "rendered_at"]
    list_filter = ["kind", "status", "engine"]
    readonly_fields = ["created_at", "updated_at", "rendered_at"]

    def has_add_permission(self, request):
        return False  # Jobs are created via the service layer only
