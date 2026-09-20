"""Accounts admin configuration."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

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
