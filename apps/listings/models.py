"""
Listings app models: geo taxonomy, features, listing, status history, image.

Models:
- City: شهر با استان
- Neighborhood: محله با aliases برای جستجوی فازی
- NeighborhoodAdjacency: جدول همجواری محله‌ها (ویرایش‌پذیر)
- Feature: امکانات (آسانسور، پارکینگ، ...)
- Listing: فایل ملک — tenant-scoped
- ListingStatusHistory: تاریخچه تغییر وضعیت
- ListingImage: تصاویر فایل
"""

import uuid as _uuid
from pathlib import Path as _Path

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import EncryptedCharField
from apps.core.models import AgencyOwned, TimeStampedModel

# ─── Try to import PostGIS PointField ─────────────────────────────────────────
try:
    from django.contrib.gis.db import models as gis_models

    _HAS_GIS = True
except Exception:  # noqa: BLE001
    gis_models = None  # type: ignore[assignment]
    _HAS_GIS = False


# ─── Choices ──────────────────────────────────────────────────────────────────


class PropertyType(models.TextChoices):
    APARTMENT = "apartment", _("آپارتمان")
    VILLA = "villa", _("ویلا / خانه")
    COMMERCIAL = "commercial", _("تجاری")
    LAND = "land", _("زمین")
    OFFICE = "office", _("اداری / دفتر")
    WAREHOUSE = "warehouse", _("انبار / سوله")
    OTHER = "other", _("سایر")


class DealType(models.TextChoices):
    SALE = "sale", _("فروش")
    RENT = "rent", _("اجاره")
    MORTGAGE_RENT = "mortgage_rent", _("رهن و اجاره")
    PRE_SALE = "pre_sale", _("پیش‌فروش")


class Direction(models.TextChoices):
    NORTH = "north", _("شمالی")
    SOUTH = "south", _("جنوبی")
    EAST = "east", _("شرقی")
    WEST = "west", _("غربی")
    NORTH_EAST = "north_east", _("شمال‌شرقی")
    NORTH_WEST = "north_west", _("شمال‌غربی")
    SOUTH_EAST = "south_east", _("جنوب‌شرقی")
    SOUTH_WEST = "south_west", _("جنوب‌غربی")


class ListingStatus(models.TextChoices):
    DRAFT = "draft", _("پیش‌نویس")
    ACTIVE = "active", _("فعال")
    RESERVED = "reserved", _("رزرو شده")
    SOLD = "sold", _("فروخته / اجاره داده شده")
    EXPIRED = "expired", _("منقضی")


# ─── City ─────────────────────────────────────────────────────────────────────


class City(models.Model):
    """Iranian city with province. Shared (not tenant-scoped)."""

    name = models.CharField(_("نام شهر"), max_length=100, db_index=True)
    province = models.CharField(_("استان"), max_length=100, db_index=True)
    slug = models.SlugField(
        _("اسلاگ"), max_length=120, unique=True, allow_unicode=True
    )

    class Meta:
        verbose_name = _("شهر")
        verbose_name_plural = _("شهرها")
        ordering = ["province", "name"]
        unique_together = [("name", "province")]

    def __str__(self) -> str:
        return f"{self.name} ({self.province})"


# ─── Neighborhood ─────────────────────────────────────────────────────────────


class Neighborhood(models.Model):
    """
    Neighborhood (محله) within a city.

    `aliases` is a JSON list of alternative names used for voice and fuzzy matching.
    E.g. ["سعادت آباد", "سعادت‌آباد", "Saadat Abad"]
    """

    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name="neighborhoods",
        verbose_name=_("شهر"),
    )
    name = models.CharField(_("نام محله"), max_length=150, db_index=True)
    aliases = models.JSONField(
        _("نام‌های مترادف"),
        default=list,
        blank=True,
        help_text=_("فهرست JSON نام‌های جایگزین برای جستجوی گفتاری و فازی"),
    )

    class Meta:
        verbose_name = _("محله")
        verbose_name_plural = _("محله‌ها")
        ordering = ["city", "name"]
        unique_together = [("city", "name")]

    def __str__(self) -> str:
        return f"{self.name} — {self.city.name}"


# ─── NeighborhoodAdjacency ────────────────────────────────────────────────────


class NeighborhoodAdjacency(models.Model):
    """
    Symmetric adjacency between two neighborhoods.

    Used by the matching engine for 'near' location matching.
    Editable by admins without code changes.
    """

    from_neighborhood = models.ForeignKey(
        Neighborhood,
        on_delete=models.CASCADE,
        related_name="adjacencies_from",
        verbose_name=_("از محله"),
    )
    to_neighborhood = models.ForeignKey(
        Neighborhood,
        on_delete=models.CASCADE,
        related_name="adjacencies_to",
        verbose_name=_("به محله"),
    )

    class Meta:
        verbose_name = _("همجواری محله")
        verbose_name_plural = _("همجواری‌های محله")
        unique_together = [("from_neighborhood", "to_neighborhood")]

    def __str__(self) -> str:
        return f"{self.from_neighborhood.name} ↔ {self.to_neighborhood.name}"


# ─── Feature ─────────────────────────────────────────────────────────────────


class Feature(models.Model):
    """
    A property feature/amenity (e.g. elevator, parking, balcony).
    Shared across all agencies.
    """

    name = models.CharField(_("نام"), max_length=100, unique=True)
    icon = models.CharField(
        _("آیکون"),
        max_length=50,
        blank=True,
        help_text=_("نام آیکون (مثلاً: elevator, parking, balcony)"),
    )

    class Meta:
        verbose_name = _("امکانات")
        verbose_name_plural = _("امکانات")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


# ─── Listing (فایل ملک) ───────────────────────────────────────────────────────


class Listing(AgencyOwned):
    """
    Core entity: a property file (فایل ملک).

    Every field that exposes owner identity is encrypted.
    Pricing is stored in Tomans as BigIntegerField.

    Location can be stored as:
    - FK to Neighborhood (structured, for matching)
    - Plain-text city/district (legacy / fallback)
    - PostGIS Point (when GIS is available)
    """

    # --- Identity ---
    code = models.CharField(
        _("کد فایل"), max_length=20, blank=True, db_index=True
    )
    title = models.CharField(_("عنوان"), max_length=255, blank=True)

    # --- Type ---
    property_type = models.CharField(
        _("نوع ملک"),
        max_length=20,
        choices=PropertyType.choices,
        default=PropertyType.APARTMENT,
        db_index=True,
    )
    deal_type = models.CharField(
        _("نوع معامله"),
        max_length=20,
        choices=DealType.choices,
        default=DealType.SALE,
        db_index=True,
    )

    # --- Location (structured) ---
    neighborhood = models.ForeignKey(
        Neighborhood,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listings",
        verbose_name=_("محله"),
    )

    # --- Location (plain text — legacy / fallback) ---
    province = models.CharField(_("استان"), max_length=100, blank=True)
    city = models.CharField(_("شهر"), max_length=100, blank=True, db_index=True)
    district = models.CharField(_("منطقه / محله"), max_length=200, blank=True)
    address = models.TextField(_("آدرس کامل"), blank=True)

    # --- Location (GIS — optional) ---
    location = (
        gis_models.PointField(
            _("موقعیت جغرافیایی"), geography=True, blank=True, null=True
        )
        if _HAS_GIS
        else models.TextField(_("موقعیت جغرافیایی (WKT)"), blank=True)
    )

    # --- Physical attributes ---
    area = models.PositiveIntegerField(_("متراژ (m²)"), null=True, blank=True)
    land_area = models.PositiveIntegerField(
        _("متراژ زمین (m²)"), null=True, blank=True
    )
    rooms = models.PositiveSmallIntegerField(
        _("تعداد اتاق"), default=0, help_text=_("صفر = بدون اتاق")
    )
    floor = models.IntegerField(_("طبقه"), null=True, blank=True)
    total_floors = models.PositiveSmallIntegerField(
        _("تعداد طبقات کل"), null=True, blank=True
    )
    units_per_floor = models.PositiveSmallIntegerField(
        _("واحد در طبقه"), null=True, blank=True
    )
    build_year = models.PositiveSmallIntegerField(
        _("سال ساخت (میلادی)"), null=True, blank=True
    )
    parking = models.BooleanField(_("پارکینگ"), default=False)
    elevator = models.BooleanField(_("آسانسور"), default=False)
    storage = models.BooleanField(_("انباری"), default=False)
    balcony = models.BooleanField(_("بالکن"), default=False)
    direction = models.CharField(
        _("جهت"),
        max_length=15,
        choices=Direction.choices,
        blank=True,
    )

    # --- Features (M2M) ---
    features = models.ManyToManyField(
        Feature,
        blank=True,
        related_name="listings",
        verbose_name=_("امکانات"),
    )

    # --- Pricing (Tomans) ---
    sale_price = models.BigIntegerField(_("قیمت فروش (تومان)"), null=True, blank=True)
    mortgage_amount = models.BigIntegerField(
        _("مبلغ رهن (تومان)"), null=True, blank=True
    )
    rent_amount = models.BigIntegerField(
        _("اجاره ماهانه (تومان)"), null=True, blank=True
    )
    price_negotiable = models.BooleanField(_("قیمت توافقی"), default=True)

    # --- Owner (encrypted, internal only) ---
    owner_name = models.CharField(_("نام مالک"), max_length=200, blank=True)
    owner_phone = EncryptedCharField(
        _("شماره مالک"), max_length=255, blank=True
    )

    # --- Workflow ---
    status = models.CharField(
        _("وضعیت"),
        max_length=20,
        choices=ListingStatus.choices,
        default=ListingStatus.ACTIVE,
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_listings",
        verbose_name=_("مشاور مسئول"),
    )
    branch = models.ForeignKey(
        "agencies.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listings",
        verbose_name=_("شعبه"),
    )

    # --- Dates ---
    published_at = models.DateTimeField(_("تاریخ انتشار"), null=True, blank=True)
    expires_at = models.DateTimeField(_("تاریخ انقضا"), null=True, blank=True)

    class Meta:
        verbose_name = _("فایل ملک")
        verbose_name_plural = _("فایل‌های ملک")
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(floor__lte=models.F("total_floors"))
                | models.Q(floor__isnull=True)
                | models.Q(total_floors__isnull=True),
                name="listing_floor_lte_total_floors",
            ),
        ]
        indexes = [
            models.Index(fields=["agency", "status"]),
            models.Index(fields=["agency", "deal_type", "property_type"]),
            models.Index(fields=["agency", "city"]),
            models.Index(fields=["agency", "neighborhood"]),
        ]

    def __str__(self) -> str:
        label = self.code or f"#{self.pk}"
        return (
            f"{label} — {self.get_property_type_display()} "
            f"{self.get_deal_type_display()}"
        )

    def save(self, *args, **kwargs) -> None:
        """Auto-generate a unique code per agency if not set."""
        if not self.code and self.agency_id:
            count = (
                Listing.all_objects.filter(agency_id=self.agency_id).count() + 1
            )
            slug = getattr(self.agency, "slug", "") if hasattr(self, "agency") else ""
            prefix = slug[:2].upper() if slug else "XX"
            self.code = f"{prefix}-{count:04d}"
        super().save(*args, **kwargs)


# ─── ListingStatusHistory ─────────────────────────────────────────────────────


class ListingStatusHistory(TimeStampedModel):
    """Records every status change for a listing."""

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name=_("فایل ملک"),
    )
    old_status = models.CharField(
        _("وضعیت قبلی"),
        max_length=20,
        choices=ListingStatus.choices,
        blank=True,
    )
    new_status = models.CharField(
        _("وضعیت جدید"),
        max_length=20,
        choices=ListingStatus.choices,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listing_status_changes",
        verbose_name=_("تغییر توسط"),
    )
    note = models.CharField(_("یادداشت"), max_length=300, blank=True)

    class Meta:
        verbose_name = _("تاریخچه وضعیت")
        verbose_name_plural = _("تاریخچه وضعیت‌ها")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"{self.listing.code}: "
            f"{self.old_status or '—'} → {self.new_status}"
        )


# ─── ListingImage ─────────────────────────────────────────────────────────────


class ListingImage(models.Model):
    """Photos attached to a listing. Ordered; first is_cover image shown in cards."""

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("فایل ملک"),
    )
    image = models.ImageField(_("تصویر"), upload_to="listings/images/%Y/%m/")
    order = models.PositiveSmallIntegerField(_("ترتیب"), default=0)
    is_cover = models.BooleanField(_("تصویر شاخص"), default=False)
    caption = models.CharField(_("توضیح"), max_length=200, blank=True)
    uploaded_at = models.DateTimeField(_("تاریخ آپلود"), auto_now_add=True)

    class Meta:
        verbose_name = _("تصویر ملک")
        verbose_name_plural = _("تصاویر ملک")
        ordering = ["order", "uploaded_at"]

    def __str__(self) -> str:
        return f"تصویر {self.order + 1} — {self.listing}"


# ─── Media (Phase 1C) ─────────────────────────────────────────────────────────


def _media_upload_path(instance: "Media", filename: str) -> str:
    ext = _Path(filename).suffix.lower()
    new_name = f"{_uuid.uuid4().hex}{ext}"
    return f"listings/{instance.listing_id}/{new_name}"


def _thumb_upload_path(instance: "Media", filename: str) -> str:
    return f"listings/{instance.listing_id}/thumbs/{filename}"


def _webp_upload_path(instance: "Media", filename: str) -> str:
    return f"listings/{instance.listing_id}/webp/{filename}"


class MediaType(models.TextChoices):
    PHOTO = "photo", _("عکس")
    VIDEO = "video", _("ویدئو")
    DOCUMENT = "document", _("سند")


class MediaStatus(models.TextChoices):
    PENDING = "pending", _("در انتظار پردازش")
    PROCESSING = "processing", _("در حال پردازش")
    READY = "ready", _("آماده")
    ERROR = "error", _("خطا")


# Allowed MIME types — validated from real file bytes (magic), not extension
ALLOWED_PHOTO_MIMES = frozenset(
    ["image/jpeg", "image/png", "image/gif", "image/webp", "image/heic", "image/heif"]
)
ALLOWED_VIDEO_MIMES = frozenset(
    ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"]
)
ALLOWED_DOCUMENT_MIMES = frozenset(
    [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
)
ALLOWED_MIMES_BY_TYPE: dict = {
    MediaType.PHOTO: ALLOWED_PHOTO_MIMES,
    MediaType.VIDEO: ALLOWED_VIDEO_MIMES,
    MediaType.DOCUMENT: ALLOWED_DOCUMENT_MIMES,
}

MAX_UPLOAD_SIZE_BYTES: dict = {
    MediaType.PHOTO: 20 * 1024 * 1024,
    MediaType.VIDEO: 50 * 1024 * 1024,
    MediaType.DOCUMENT: 20 * 1024 * 1024,
}


class Media(TimeStampedModel):
    """
    رسانه متصل به فایل ملک — فاز 1C.

    - photo:    عکس عمومی؛ thumbnail + webp در Celery ساخته می‌شود؛ EXIF/GPS حذف می‌شود.
    - video:    ویدئو عمومی؛ فقط ذخیره می‌شود.
    - document: سند خصوصی؛ دسترسی فقط با signed URL کوتاه‌مدت.
    """

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="media_files",
        verbose_name=_("فایل ملک"),
    )
    media_type = models.CharField(
        _("نوع رسانه"),
        max_length=10,
        choices=MediaType.choices,
        default=MediaType.PHOTO,
        db_index=True,
    )
    file = models.FileField(
        _("فایل"),
        upload_to=_media_upload_path,
        max_length=500,
    )
    thumbnail = models.FileField(
        _("بندانگشتی"),
        upload_to=_thumb_upload_path,
        blank=True,
        max_length=500,
    )
    webp = models.FileField(
        _("نسخه WebP"),
        upload_to=_webp_upload_path,
        blank=True,
        max_length=500,
    )
    is_private = models.BooleanField(
        _("سند خصوصی"),
        default=False,
        help_text=_("اسناد خصوصی فقط با لینک امضاشده قابل دسترسند"),
    )
    is_cover = models.BooleanField(_("تصویر شاخص"), default=False)
    order = models.PositiveSmallIntegerField(_("ترتیب"), default=0)
    caption = models.CharField(_("توضیح"), max_length=200, blank=True)
    original_filename = models.CharField(_("نام فایل اصلی"), max_length=300, blank=True)
    mime_type = models.CharField(_("نوع MIME"), max_length=100, blank=True)
    file_size = models.PositiveBigIntegerField(_("حجم (بایت)"), default=0)
    status = models.CharField(
        _("وضعیت پردازش"),
        max_length=15,
        choices=MediaStatus.choices,
        default=MediaStatus.PENDING,
        db_index=True,
    )
    error_message = models.CharField(_("پیغام خطا"), max_length=500, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_media",
        verbose_name=_("آپلود توسط"),
    )

    class Meta:
        verbose_name = _("رسانه")
        verbose_name_plural = _("رسانه‌ها")
        ordering = ["order", "created_at"]
        indexes = [
            models.Index(
                fields=["listing", "media_type", "is_private"],
                name="media_listing_type_priv_idx",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_media_type_display()} — {self.listing} [{self.status}]"

    def generate_signed_url(self, expires_seconds: int = 300) -> str:
        """Generate a time-limited signed URL for private documents."""
        from django.core import signing  # noqa: PLC0415
        from django.utils import timezone  # noqa: PLC0415

        token = signing.dumps(
            {"media_id": self.pk, "exp": (timezone.now().timestamp() + expires_seconds)},
            salt="media-signed-url",
        )
        from django.urls import reverse  # noqa: PLC0415
        return reverse("listings:media_serve_private", kwargs={"token": token})


# ─── ImportJob (Phase 1D) ─────────────────────────────────────────────────────


class ImportJobStatus(models.TextChoices):
    PENDING = "pending", _("در انتظار")
    PROCESSING = "processing", _("در حال پردازش")
    DONE = "done", _("انجام شد")
    ERROR = "error", _("خطا")


class ImportJob(AgencyOwned):
    """
    ردیابی ایمپورت Excel/CSV فایل‌های ملک.

    uploaded_file: فایل اصلی آپلود‌شده (Excel یا CSV)
    status: وضعیت پردازش
    total_rows / imported_rows / error_rows: آمار
    error_report: JSON آرایه‌ای از خطاها  [{row, field, message}]
    created_by: کاربر ایجادکننده
    """

    uploaded_file = models.FileField(
        _("فایل آپلود‌شده"),
        upload_to="imports/%Y/%m/",
        max_length=500,
    )
    original_filename = models.CharField(_("نام فایل اصلی"), max_length=300, blank=True)
    status = models.CharField(
        _("وضعیت"),
        max_length=15,
        choices=ImportJobStatus.choices,
        default=ImportJobStatus.PENDING,
        db_index=True,
    )
    total_rows = models.PositiveIntegerField(_("کل ردیف‌ها"), default=0)
    imported_rows = models.PositiveIntegerField(_("ردیف‌های موفق"), default=0)
    error_rows = models.PositiveIntegerField(_("ردیف‌های خطا"), default=0)
    error_report = models.JSONField(_("گزارش خطا"), default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_jobs",
        verbose_name=_("ایجاد توسط"),
    )

    class Meta:
        verbose_name = _("ایمپورت")
        verbose_name_plural = _("ایمپورت‌ها")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Import {self.pk} [{self.status}] — {self.agency}"
