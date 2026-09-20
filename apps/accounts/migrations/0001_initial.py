"""Accounts initial migration."""

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("agencies", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomUser",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, verbose_name="superuser status")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")),
                ("phone", models.CharField(max_length=15, unique=True, verbose_name="شماره موبایل")),
                ("full_name", models.CharField(blank=True, max_length=150, verbose_name="نام کامل")),
                ("email", models.EmailField(blank=True, verbose_name="ایمیل")),
                ("agency", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="users",
                    to="agencies.agency",
                    verbose_name="آژانس",
                )),
                ("role", models.CharField(
                    choices=[("superadmin", "سوپرادمین"), ("owner", "مالک آژانس"), ("agent", "مشاور"), ("viewer", "مشاهده‌گر")],
                    default="agent",
                    max_length=20,
                    verbose_name="نقش",
                )),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
                ("is_staff", models.BooleanField(default=False, verbose_name="کارمند سیستم")),
                ("groups", models.ManyToManyField(
                    blank=True,
                    related_name="customuser_set",
                    related_query_name="customuser",
                    to="auth.group",
                    verbose_name="groups",
                )),
                ("user_permissions", models.ManyToManyField(
                    blank=True,
                    related_name="customuser_set",
                    related_query_name="customuser",
                    to="auth.permission",
                    verbose_name="user permissions",
                )),
            ],
            options={"verbose_name": "کاربر", "verbose_name_plural": "کاربران"},
        ),
    ]
