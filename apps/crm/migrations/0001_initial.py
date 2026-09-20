"""
crm 0001 initial migration — Request table.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("agencies", "0001_initial"),
        ("listings", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Request",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")),
                ("client_name", models.CharField(max_length=200, verbose_name="نام مراجعه‌کننده")),
                ("client_phone", models.CharField(blank=True, max_length=255, verbose_name="شماره مراجعه‌کننده")),
                ("source", models.CharField(
                    choices=[
                        ("walk_in", "مراجعه حضوری"), ("referral", "معرفی"),
                        ("portal", "پورتال"), ("social", "شبکه اجتماعی"),
                        ("direct", "تماس مستقیم"), ("other", "سایر"),
                    ],
                    default="walk_in", max_length=20, verbose_name="منبع مراجعه",
                )),
                ("deal_type", models.CharField(
                    choices=[
                        ("sale", "فروش"), ("rent", "اجاره"),
                        ("mortgage_rent", "رهن و اجاره"), ("pre_sale", "پیش‌فروش"),
                    ],
                    db_index=True, default="sale", max_length=20, verbose_name="نوع معامله",
                )),
                ("property_types", models.JSONField(blank=True, default=list, verbose_name="نوع ملک موردنظر")),
                ("min_area", models.PositiveIntegerField(blank=True, null=True, verbose_name="حداقل متراژ")),
                ("max_area", models.PositiveIntegerField(blank=True, null=True, verbose_name="حداکثر متراژ")),
                ("min_rooms", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="حداقل اتاق")),
                ("max_rooms", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="حداکثر اتاق")),
                ("city", models.CharField(blank=True, db_index=True, max_length=100, verbose_name="شهر")),
                ("district", models.CharField(blank=True, max_length=200, verbose_name="منطقه / محله")),
                ("min_budget", models.BigIntegerField(blank=True, null=True, verbose_name="حداقل بودجه (تومان)")),
                ("max_budget", models.BigIntegerField(blank=True, null=True, verbose_name="حداکثر بودجه (تومان)")),
                ("notes", models.TextField(blank=True, verbose_name="توضیحات")),
                ("status", models.CharField(
                    choices=[
                        ("new", "جدید"), ("in_progress", "در حال پیگیری"),
                        ("matched", "تطبیق یافته"), ("closed", "بسته شده"),
                        ("cancelled", "لغو شده"),
                    ],
                    db_index=True, default="new", max_length=20, verbose_name="وضعیت",
                )),
                ("priority", models.CharField(
                    choices=[
                        ("low", "کم"), ("normal", "معمولی"),
                        ("high", "بالا"), ("urgent", "فوری"),
                    ],
                    db_index=True, default="normal", max_length=10, verbose_name="اولویت",
                )),
                ("contacted_at", models.DateTimeField(blank=True, null=True, verbose_name="آخرین تماس")),
                ("closed_at", models.DateTimeField(blank=True, null=True, verbose_name="تاریخ بستن")),
                ("agency", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="crm_request_set",
                    to="agencies.agency",
                    verbose_name="آژانس",
                )),
                ("assigned_to", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="assigned_requests",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="مشاور مسئول",
                )),
            ],
            options={
                "verbose_name": "درخواست",
                "verbose_name_plural": "درخواست‌ها",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="request",
            index=models.Index(fields=["agency", "status"], name="crm_request_agency_status_idx"),
        ),
        migrations.AddIndex(
            model_name="request",
            index=models.Index(fields=["agency", "deal_type"], name="crm_request_agency_deal_idx"),
        ),
        migrations.AddIndex(
            model_name="request",
            index=models.Index(fields=["agency", "priority", "status"], name="crm_request_agency_prio_idx"),
        ),
    ]
