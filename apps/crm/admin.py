"""
CRM Django admin.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.crm.models import (
    ConsentRecord,
    Contact,
    ContactPhone,
    Interaction,
    Notification,
    Request,
    Task,
    Visit,
)


class ContactPhoneInline(admin.TabularInline):
    model = ContactPhone
    extra = 0
    fields = ("phone", "phone_normalized", "label", "is_primary")


class ConsentRecordInline(admin.TabularInline):
    model = ConsentRecord
    extra = 0
    fields = (
        "channel", "source", "granted_at", "text_version",
        "recorded_by", "revoked_at", "revoke_reason",
    )
    readonly_fields = ("granted_at", "created_at")
    ordering = ("-granted_at",)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "full_name", "contact_type", "agency",
        "phone_normalized", "is_active", "created_at",
    )
    list_filter = ("contact_type", "agency", "is_active")
    search_fields = ("full_name", "phone_normalized", "email")
    readonly_fields = ("created_at", "updated_at", "merged_into")
    inlines = [ContactPhoneInline, ConsentRecordInline]
    fieldsets = (
        (None, {"fields": ("agency", "full_name", "contact_type", "is_active")}),
        (_("تماس"), {"fields": ("phone", "phone_normalized", "email")}),
        (_("یادداشت"), {"fields": ("notes",)}),
        (_("ادغام"), {"fields": ("merged_into",), "classes": ("collapse",)}),
        (_("تاریخ‌ها"), {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = (
        "contact", "agency", "channel", "source",
        "granted_at", "is_active", "revoked_at",
    )
    list_filter = ("channel", "source", "agency")
    search_fields = ("contact__full_name",)
    readonly_fields = ("granted_at", "created_at", "updated_at")

    def has_change_permission(self, request, obj=None):
        # Consent records are append-only; only allow revoke via revoke()
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = (
        "client_name", "agency", "contact", "deal_type",
        "city", "status", "priority", "assigned_to", "created_at",
    )
    list_filter = ("status", "deal_type", "priority", "source", "agency")
    search_fields = ("client_name", "city", "notes")
    readonly_fields = ("created_at", "updated_at", "closed_at")
    autocomplete_fields = ["contact"]
    fieldsets = (
        (_("مراجعه‌کننده"), {
            "fields": ("agency", "contact", "client_name", "client_phone", "source"),
        }),
        (_("نیاز"), {"fields": (
            "deal_type", "property_types",
            "min_area", "max_area", "min_rooms", "max_rooms",
            "city", "district", "min_budget", "max_budget", "notes",
        )}),
        (_("وضعیت"), {"fields": ("status", "priority", "assigned_to")}),
        (_("تاریخ‌ها"), {
            "fields": ("expires_at", "contacted_at", "closed_at", "created_at", "updated_at"),
        }),
    )


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ("kind", "summary", "agency", "contact", "listing", "request", "occurred_at")
    list_filter = ("kind", "agency", "occurred_at")
    search_fields = ("summary", "detail")
    raw_id_fields = ("contact", "listing", "request", "performed_by")
    date_hierarchy = "occurred_at"
    readonly_fields = ("created_at", "updated_at")


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = (
        "contact", "listing", "agency", "scheduled_at", "status", "outcome", "agent",
    )
    list_filter = ("status", "outcome", "agency")
    search_fields = ("note", "contact__full_name")
    raw_id_fields = ("listing", "contact", "request", "agent")
    date_hierarchy = "scheduled_at"
    readonly_fields = ("created_at", "updated_at")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "assignee", "agency", "due_at", "priority", "status", "completed_at")
    list_filter = ("status", "priority", "agency")
    search_fields = ("title", "description")
    raw_id_fields = ("assignee", "related_contact", "related_listing", "related_request")
    date_hierarchy = "due_at"
    readonly_fields = ("created_at", "updated_at", "reminder_sent_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "agency", "kind", "is_read", "created_at")
    list_filter = ("kind", "is_read", "agency")
    search_fields = ("title", "body")
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at", "read_at")
