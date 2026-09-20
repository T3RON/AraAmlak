from django.contrib import admin

from apps.matching.models import Match


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("id", "agency", "request", "listing", "score", "created_at")
    list_filter = ("agency", "score")
    search_fields = ("request__client_name", "listing__code")
    ordering = ("-score", "-created_at")
    readonly_fields = ("created_at", "updated_at")
