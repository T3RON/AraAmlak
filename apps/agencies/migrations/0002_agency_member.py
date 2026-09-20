"""
Add AgencyMember table.

Separate from 0001_initial to break the circular dependency between
agencies (needs AUTH_USER_MODEL) and accounts (needs agencies.Agency).
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("agencies", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AgencyMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="agency_memberships",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="کاربر",
                )),
                ("agency", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="members",
                    to="agencies.agency",
                    verbose_name="آژانس",
                )),
                ("role", models.CharField(
                    choices=[("owner", "مالک"), ("agent", "مشاور"), ("viewer", "مشاهده‌گر")],
                    default="agent", max_length=20, verbose_name="نقش",
                )),
                ("joined_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ عضویت")),
            ],
            options={
                "verbose_name": "عضو آژانس",
                "verbose_name_plural": "اعضای آژانس",
                "unique_together": {("user", "agency")},
            },
        ),
    ]
