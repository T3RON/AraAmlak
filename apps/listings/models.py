"""
Listings app models: Listing (فایل ملک) and ListingImage.

Every Listing is tenant-scoped via AgencyOwned.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import EncryptedCharField
from apps.core.models import AgencyOwned

# ─── Try to import PostGIS PointField ─────────────────────────────────────────
try:

    _HAS_GIS = True
except Exception:  # noqa: BLE001
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


# ─── Listing (فایل ملک) ───────────────────────────────────────────────────────


class Listing(AgencyOwned):
    """
    Core entity: a property file (فایل ملک).

    Every field that exposes owner identity is encrypted.
    Pricing is stored in Tomans as BigIntegerField.
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

    # --- Location ---
    province = models.CharField(_("استان"), max_length=100, blank=True)
    city = models.CharField(_("شهر"), max_length=100, blank=True, db_index=True)
    district = models.CharField(_("منطقه / محله"), max_length=200, blank=True)
    address = models.TextField(_("آدرس کامل"), blank=True)

    # --- Physical attributes ---
    area = models.PositiveIntegerField(_("متراژ (m²)"), null=True, blank=True)
    rooms = models.PositiveSmallIntegerField(
        _("تعداد اتاق"), default=0, help_text=_("صفر = بدون اتاق")
    )
    floor = models.IntegerField(_("طبقه"), null=True, blank=True)
    total_floors = models.PositiveSmallIntegerField(
        _("تعداد طبقات کل"), null=True, blank=True
    )
    build_year = models.PositiveSmallIntegerField(
        _("سال ساخت (میلادی)"), null=True, blank=True
    )
    parking = models.BooleanField(_("پارکینگ"), default=False)
    elevator = models.BooleanField(_("آسانسور"), default=False)
    storage = models.BooleanField(_("انباری"), default=False)
    direction = models.CharField(
        _("جهت"),
        max_length=15,
        choices=Direction.choices,
        blank=True,
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
        indexes = [
            models.Index(fields=["agency", "status"]),
            models.Index(fields=["agency", "deal_type", "property_type"]),
            models.Index(fields=["agency", "city"]),
        ]

    def __str__(self) -> str:
        label = self.code or f"#{self.pk}"
        return f"{label} — {self.get_property_type_display()} {self.get_deal_type_display()}"

    def save(self, *args, **kwargs) -> None:
        """Auto-generate a unique code per agency if not set."""
        if not self.code and self.agency_id:
            count = (
                Listing.all_objects.filter(agency_id=self.agency_id).count() + 1
            )
            # Use first 2 uppercase letters of agency slug as prefix
            slug = getattr(self.agency, "slug", "") if hasattr(self, "agency") else ""
            prefix = (slug[:2].upper() if slug else "XX")
            self.code = f"{prefix}-{count:04d}"
        super().save(*args, **kwargs)


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
    uploaded_at = models.DateTimeField(_("تاریخ آپلود"), auto_now_add=True)

    class Meta:
        verbose_name = _("تصویر ملک")
        verbose_name_plural = _("تصاویر ملک")
        ordering = ["order", "uploaded_at"]

    def __str__(self) -> str:
        return f"تصویر {self.order + 1} — {self.listing}"
