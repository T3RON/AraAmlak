"""
Agencies initial migration — Agency and Branch tables only.

AgencyMember is in 0002_agency_member to avoid circular dependency with accounts.
Branch.location is TextField on SQLite; PointField migration is done separately on PostGIS.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("core", "0001_extensions"),
    ]

    operations = [
        migrations.CreateModel(
            name="Agency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")),
                ("name", models.CharField(max_length=200, verbose_name="نام")),
                ("slug", models.SlugField(max_length=80, unique=True, verbose_name="اسلاگ")),
                ("logo", models.ImageField(blank=True, null=True, upload_to="agencies/logos/", verbose_name="لوگو")),
                ("phone", models.CharField(blank=True, max_length=20, verbose_name="تلفن")),
                ("address", models.TextField(blank=True, verbose_name="آدرس")),
                ("plan", models.CharField(
                    choices=[("free", "رایگان"), ("pro", "حرفه‌ای"), ("enterprise", "سازمانی")],
                    default="free", max_length=20, verbose_name="پلن",
                )),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
            ],
            options={"verbose_name": "آژانس", "verbose_name_plural": "آژانس‌ها", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Branch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")),
                ("agency", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="branches",
                    to="agencies.agency",
                    verbose_name="آژانس",
                )),
                ("name", models.CharField(max_length=200, verbose_name="نام شعبه")),
                ("address", models.TextField(blank=True, verbose_name="آدرس")),
                # TextField fallback for SQLite; PostGIS migration adds PointField separately
                ("location", models.TextField(verbose_name="موقعیت جغرافیایی (WKT)", blank=True)),
                ("phone", models.CharField(blank=True, max_length=20, verbose_name="تلفن")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
            ],
            options={"verbose_name": "شعبه", "verbose_name_plural": "شعبه‌ها", "ordering": ["agency", "name"]},
        ),
    ]
