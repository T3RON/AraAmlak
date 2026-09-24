"""Admin for the AI app."""

from django.contrib import admin

from .models import AgencyAIConfig, VoiceDraft, VoiceNote


@admin.register(AgencyAIConfig)
class AgencyAIConfigAdmin(admin.ModelAdmin):
    list_display = ["agency", "provider", "model_name", "is_active"]
    list_filter = ["provider", "is_active"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(VoiceNote)
class VoiceNoteAdmin(admin.ModelAdmin):
    list_display = [
        "pk",
        "agency",
        "status",
        "provider",
        "file_size",
        "listing",
        "created_at",
    ]
    list_filter = ["status", "provider"]
    search_fields = ["original_filename", "transcript"]
    readonly_fields = ["created_at", "updated_at", "transcribed_at"]


@admin.register(VoiceDraft)
class VoiceDraftAdmin(admin.ModelAdmin):
    list_display = ["pk", "agency", "voice_note", "status", "confidence", "listing"]
    list_filter = ["status"]
    readonly_fields = ["created_at", "updated_at"]
