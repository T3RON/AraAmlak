"""
listings 0001 initial migration — Listing + ListingImage tables.
"""

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("agencies", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Listing",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")),
                ("code", models.CharField(blank=True, db_index=True, max_length=20, verbose_name="کد فایل")),
                ("title", models.CharField(blank=True, max_length=255, verbose_name="عنوان")),
                ("property_type", models.CharField(
                    choices=[
                        ("apartment", "آپارتمان"), ("villa", "ویلا / خانه"),
                        ("commercial", "تجاری"), ("land", "زمین"),
                        ("office", "اداری / دفتر"), ("warehouse", "انبار / سوله"),
                        ("other", "سایر"),
                    ],
                    db_index=True, default="apartment", max_length=20, verbose_name="نوع ملک",
                )),
                ("deal_type", models.CharField(
                    choices=[
                        ("sale", "فروش"), ("rent", "اجاره"),
                        ("mortgage_rent", "رهن و اجاره"), ("pre_sale", "پیش‌فروش"),
                    ],
                    db_index=True, default="sale", max_length=20, verbose_name="نوع معامله",
                )),
                ("province", models.CharField(blank=True, max_length=100, verbose_name="استان")),
                ("city", models.CharField(blank=True, db_index=True, max_length=100, verbose_name="شهر")),
                ("district", models.CharField(blank=True, max_length=200, verbose_name="منطقه / محله")),
                ("address", models.TextField(blank=True, verbose_name="آدرس کامل")),
                ("area", models.PositiveIntegerField(blank=True, null=True, verbose_name="متراژ (m²)")),
                ("rooms", models.PositiveSmallIntegerField(default=0, verbose_name="تعداد اتاق")),
                ("floor", models.IntegerField(blank=True, null=True, verbose_name="طبقه")),
                ("total_floors", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="تعداد طبقات کل")),
                ("build_year", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="سال ساخت (میلادی)")),
                ("parking", models.BooleanField(default=False, verbose_name="پارکینگ")),
                ("elevator", models.BooleanField(default=False, verbose_name="آسانسور")),
                ("storage", models.BooleanField(default=False, verbose_name="انباری")),
                ("direction", models.CharField(
                    blank=True, max_length=15,
                    choices=[
                        ("north", "شمالی"), ("south", "جنوبی"),
                        ("east", "شرقی"), ("west", "غربی"),
                        ("north_east", "شمال‌شرقی"), ("north_west", "شمال‌غربی"),
                        ("south_east", "جنوب‌شرقی"), ("south_west", "جنوب‌غربی"),
                    ],
                    verbose_name="جهت",
                )),
                ("sale_price", models.BigIntegerField(blank=True, null=True, verbose_name="قیمت فروش (تومان)")),
                ("mortgage_amount", models.BigIntegerField(blank=True, null=True, verbose_name="مبلغ رهن (تومان)")),
                ("rent_amount", models.BigIntegerField(blank=True, null=True, verbose_name="اجاره ماهانه (تومان)")),
                ("price_negotiable", models.BooleanField(default=True, verbose_name="قیمت توافقی")),
                ("owner_name", models.CharField(blank=True, max_length=200, verbose_name="نام مالک")),
                ("owner_phone", models.CharField(blank=True, max_length=255, verbose_name="شماره مالک")),
                ("status", models.CharField(
                    choices=[
                        ("draft", "پیش‌نویس"), ("active", "فعال"),
                        ("reserved", "رزرو شده"), ("sold", "فروخته / اجاره داده شده"),
                        ("expired", "منقضی"),
                    ],
                    db_index=True, default="active", max_length=20, verbose_name="وضعیت",
                )),
                ("published_at", models.DateTimeField(blank=True, null=True, verbose_name="تاریخ انتشار")),
                ("expires_at", models.DateTimeField(blank=True, null=True, verbose_name="تاریخ انقضا")),
                ("agency", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="listings_listing_set",
                    to="agencies.agency",
                    verbose_name="آژانس",
                    db_index=True,
                )),
                ("assigned_to", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="assigned_listings",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="مشاور مسئول",
                )),
                ("branch", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="listings",
                    to="agencies.branch",
                    verbose_name="شعبه",
                )),
            ],
            options={
                "verbose_name": "فایل ملک",
                "verbose_name_plural": "فایل‌های ملک",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="listing",
            index=models.Index(fields=["agency", "status"], name="listings_li_agency_status_idx"),
        ),
        migrations.AddIndex(
            model_name="listing",
            index=models.Index(fields=["agency", "deal_type", "property_type"], name="listings_li_agency_deal_prop_idx"),
        ),
        migrations.AddIndex(
            model_name="listing",
            index=models.Index(fields=["agency", "city"], name="listings_li_agency_city_idx"),
        ),
        migrations.CreateModel(
            name="ListingImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="listings/images/%Y/%m/", verbose_name="تصویر")),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")),
                ("is_cover", models.BooleanField(default=False, verbose_name="تصویر شاخص")),
                ("uploaded_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ آپلود")),
                ("listing", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="images",
                    to="listings.listing",
                    verbose_name="فایل ملک",
                )),
            ],
            options={
                "verbose_name": "تصویر ملک",
                "verbose_name_plural": "تصاویر ملک",
                "ordering": ["order", "uploaded_at"],
            },
        ),
    ]
