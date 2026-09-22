"""Accounts admin configuration."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditLog

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    ordering = ["phone"]
    list_display = ["phone", "full_name", "agency", "role", "is_active", "is_staff"]
    list_filter = ["role", "agency", "is_active", "is_staff"]
    search_fields = ["phone", "full_name", "email"]
    readonly_fields = ["created_at", "updated_at", "last_login"]

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (_("اطلاعات شخصی"), {"fields": ("full_name", "email")}),
        (_("آژانس و نقش"), {"fields": ("agency", "role")}),
        (  # noqa: E501
            _("دسترسی‌ها"),
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        (_("تاریخ‌ها"), {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "full_name", "agency", "role", "password1", "password2"),
        }),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id", "actor", "agency", "action",
        "object_model", "object_repr", "ip_address", "created_at",
    )
    list_filter = ("action", "agency", "object_model")
    search_fields = ("actor__phone", "actor__full_name", "object_repr", "ip_address")
    readonly_fields = (
        "actor", "agency", "action", "object_model", "object_id",
        "object_repr", "diff", "ip_address", "user_agent", "extra", "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
