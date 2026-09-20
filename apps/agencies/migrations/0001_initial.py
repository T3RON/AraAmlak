"""Agencies initial migration."""

import django.contrib.gis.db.models.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("core", "0001_extensions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
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
                ("plan", models.CharField(choices=[("free", "رایگان"), ("pro", "حرفه‌ای"), ("enterprise", "سازمانی")], default="free", max_length=20, verbose_name="پلن")),
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
                ("agency", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="branches", to="agencies.agency", verbose_name="آژانس")),
                ("name", models.CharField(max_length=200, verbose_name="نام شعبه")),
                ("address", models.TextField(blank=True, verbose_name="آدرس")),
                ("location", django.contrib.gis.db.models.fields.PointField(blank=True, geography=True, null=True, srid=4326, verbose_name="موقعیت جغرافیایی")),
                ("phone", models.CharField(blank=True, max_length=20, verbose_name="تلفن")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
            ],
            options={"verbose_name": "شعبه", "verbose_name_plural": "شعبه‌ها", "ordering": ["agency", "name"]},
        ),
        migrations.CreateModel(
            name="AgencyMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="agency_memberships", to=settings.AUTH_USER_MODEL, verbose_name="کاربر")),
                ("agency", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="members", to="agencies.agency", verbose_name="آژانس")),
                ("role", models.CharField(choices=[("owner", "مالک"), ("agent", "مشاور"), ("viewer", "مشاهده‌گر")], default="agent", max_length=20, verbose_name="نقش")),
                ("joined_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ عضویت")),
            ],
            options={"verbose_name": "عضو آژانس", "verbose_name_plural": "اعضای آژانس", "unique_together": {("user", "agency")}},
        ),
    ]
