"""Admin for the messaging app."""

from django.contrib import admin

from .models import AgencySMSConfig, SMSMessage, SMSTemplate


@admin.register(AgencySMSConfig)
class AgencySMSConfigAdmin(admin.ModelAdmin):
    list_display = ["agency", "provider", "sender_line", "is_active"]
    list_filter = ["provider", "is_active"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(SMSTemplate)
class SMSTemplateAdmin(admin.ModelAdmin):
    list_display = ["agency", "name", "is_active", "segment_count_estimate"]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(SMSMessage)
class SMSMessageAdmin(admin.ModelAdmin):
    list_display = ["pk", "agency", "recipient_masked", "state", "provider", "created_at"]
    list_filter = ["state", "provider"]
    readonly_fields = [
        "recipient_masked",
        "body",
        "state",
        "provider",
        "provider_message_id",
        "sent_at",
        "delivered_at",
        "failed_at",
        "failure_reason",
        "cost",
        "segment_count",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request):
        return False  # Log is append-only via service layer

    def has_delete_permission(self, request, obj=None):
        return False
