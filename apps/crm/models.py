"""
CRM app models: Contact, ContactPhone, ConsentRecord, Request.

Models:
- ContactType: مالک / مراجعه‌کننده / سرمایه‌گذار / همکار
- Contact: مخاطب tenant-scoped با ادغام تکراری
- ContactPhone: شماره‌های نرمال‌شده مخاطب
- ConsentRecord: رضایت دریافت پیامک با audit trail
- Request: درخواست / نیازمندی مراجعه‌کننده — tenant-scoped
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.fields import EncryptedCharField
from apps.core.models import AgencyOwned, TimeStampedModel
from apps.listings.models import DealType  # reuse choice enums

# ─── Choices ──────────────────────────────────────────────────────────────────


class ContactType(models.TextChoices):
    OWNER = "owner", _("مالک")
    BUYER = "buyer", _("مراجعه‌کننده / خریدار")
    INVESTOR = "investor", _("سرمایه‌گذار")
    COLLEAGUE = "colleague", _("همکار")
    OTHER = "other", _("سایر")


class PhoneLabel(models.TextChoices):
    MOBILE = "mobile", _("موبایل")
    HOME = "home", _("منزل")
    WORK = "work", _("محل کار")
    OTHER = "other", _("سایر")


class ConsentSource(models.TextChoices):
    IN_PERSON = "in_person", _("حضوری")
    PUBLIC_FORM = "public_form", _("فرم عمومی")
    PHONE = "phone", _("تلفنی")
    OTHER = "other", _("سایر")


class RequestSource(models.TextChoices):
    WALK_IN = "walk_in", _("مراجعه حضوری")
    REFERRAL = "referral", _("معرفی")
    PORTAL = "portal", _("پورتال")
    PUBLIC_FORM = "public_form", _("فرم عمومی")
    SOCIAL = "social", _("شبکه اجتماعی")
    DIRECT = "direct", _("تماس مستقیم")
    OTHER = "other", _("سایر")


class RequestStatus(models.TextChoices):
    NEW = "new", _("جدید")
    IN_PROGRESS = "in_progress", _("در حال پیگیری")
    MATCHED = "matched", _("تطبیق یافته")
    CLOSED = "closed", _("بسته شده")
    CANCELLED = "cancelled", _("لغو شده")
    EXPIRED = "expired", _("منقضی")


class RequestPriority(models.TextChoices):
    LOW = "low", _("کم")
    NORMAL = "normal", _("معمولی")
    HIGH = "high", _("بالا")
    URGENT = "urgent", _("فوری")


# ─── Contact ──────────────────────────────────────────────────────────────────


class Contact(AgencyOwned):
    """
    A person who interacts with the agency: owner, buyer, investor, or colleague.

    phone field is the primary canonical (encrypted) phone for quick lookup.
    Additional phones in ContactPhone M2M.
    Duplicate merging: merge_into(target) reassigns all relations.
    """

    full_name = models.CharField(_("نام کامل"), max_length=200)
    contact_type = models.CharField(
        _("نوع مخاطب"),
        max_length=20,
        choices=ContactType.choices,
        default=ContactType.BUYER,
        db_index=True,
    )
    # Primary phone (encrypted at rest, indexed via normalized shadow)
    phone = EncryptedCharField(
        _("شماره اصلی"), max_length=255, blank=True
    )
    # Normalized (non-encrypted) phone for uniqueness/index — not shown in UI
    phone_normalized = models.CharField(
        _("شماره اصلی (نرمال‌شده)"),
        max_length=15,
        blank=True,
        db_index=True,
        help_text=_("برای جستجو و یکتایی — مقدار رمزنگاری‌نشده"),
    )
    email = models.EmailField(_("ایمیل"), blank=True)
    notes = models.TextField(_("یادداشت"), blank=True)
    is_active = models.BooleanField(_("فعال"), default=True)
    merged_into = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="merged_from",
        verbose_name=_("ادغام شده در"),
    )

    class Meta:
        verbose_name = _("مخاطب")
        verbose_name_plural = _("مخاطبین")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "contact_type"]),
            models.Index(fields=["agency", "phone_normalized"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.get_contact_type_display()})"

    def save(self, *args, **kwargs) -> None:
        """Auto-populate phone_normalized from phone when possible."""
        # phone is encrypted so we can't normalize at save without knowing plaintext.
        # Callers should set phone_normalized explicitly before save.
        super().save(*args, **kwargs)

    def merge_into(self, target: "Contact") -> None:
        """
        Reassign all FK/M2M relations from self to target, then soft-delete self.
        Call inside a transaction.
        """
        # Reassign phones
        ContactPhone.objects.filter(contact=self).update(contact=target)
        # Reassign requests
        Request.all_objects.filter(contact=self).update(contact=target)
        # Reassign consent records
        ConsentRecord.objects.filter(contact=self).update(contact=target)
        # Mark as merged
        self.merged_into = target
        self.is_active = False
        self.save(update_fields=["merged_into", "is_active"])


# ─── ContactPhone ─────────────────────────────────────────────────────────────


class ContactPhone(TimeStampedModel):
    """
    Additional phone numbers for a Contact.

    phone is encrypted; phone_normalized is plain for uniqueness per agency.
    """

    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="phones",
        verbose_name=_("مخاطب"),
    )
    phone = EncryptedCharField(_("شماره"), max_length=255)
    phone_normalized = models.CharField(
        _("شماره (نرمال‌شده)"),
        max_length=15,
        blank=True,
        db_index=True,
    )
    label = models.CharField(
        _("نوع"),
        max_length=10,
        choices=PhoneLabel.choices,
        default=PhoneLabel.MOBILE,
    )
    is_primary = models.BooleanField(_("اصلی"), default=False)

    class Meta:
        verbose_name = _("شماره تماس")
        verbose_name_plural = _("شماره‌های تماس")
        ordering = ["-is_primary", "label"]

    def __str__(self) -> str:
        return f"{self.contact.full_name} — {self.get_label_display()}"


# ─── ConsentRecord ────────────────────────────────────────────────────────────

_CONSENT_TEXT_VERSION = "v1"
_DEFAULT_CONSENT_TEXT = (
    "رضایت می‌دهم آژانس {agency_name} برای معرفی ملک‌های مناسب "
    "با من از طریق پیامک ارتباط برقرار کند. "
    "برای لغو می‌توانم با آژانس تماس بگیرم."
)


class ConsentRecord(TimeStampedModel):
    """
    Immutable record of a contact's consent to receive SMS.

    Append-only: never update. To revoke, set revoked_at.
    source records how/where consent was collected.
    text_version pins the exact consent text that was shown.
    """

    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="consent_records",
        verbose_name=_("مخاطب"),
    )
    agency = models.ForeignKey(
        "agencies.Agency",
        on_delete=models.CASCADE,
        related_name="consent_records",
        verbose_name=_("آژانس"),
        db_index=True,
    )
    channel = models.CharField(
        _("کانال"),
        max_length=20,
        default="sms",
        help_text=_("sms | whatsapp | ..."),
    )
    granted_at = models.DateTimeField(_("زمان رضایت"), default=timezone.now)
    source = models.CharField(
        _("منبع"),
        max_length=20,
        choices=ConsentSource.choices,
        default=ConsentSource.IN_PERSON,
    )
    text_version = models.CharField(
        _("نسخه متن رضایت"),
        max_length=20,
        default=_CONSENT_TEXT_VERSION,
    )
    consent_text = models.TextField(
        _("متن رضایت نشان داده شده"),
        blank=True,
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_consents",
        verbose_name=_("ثبت‌کننده"),
    )
    revoked_at = models.DateTimeField(_("زمان لغو"), null=True, blank=True)
    revoke_reason = models.CharField(_("دلیل لغو"), max_length=300, blank=True)

    class Meta:
        verbose_name = _("رضایت پیامک")
        verbose_name_plural = _("رضایت‌نامه‌ها")
        ordering = ["-granted_at"]
        indexes = [
            models.Index(fields=["agency", "contact", "channel"]),
            models.Index(fields=["contact", "revoked_at"]),
        ]

    def __str__(self) -> str:
        status = "فعال" if not self.revoked_at else "لغو شده"
        return f"رضایت {self.contact.full_name} — {self.channel} [{status}]"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def revoke(self, reason: str = "") -> None:
        """Revoke this consent. Does NOT delete the record."""
        if not self.revoked_at:
            self.revoked_at = timezone.now()
            self.revoke_reason = reason[:300]
            self.save(update_fields=["revoked_at", "revoke_reason"])


# ─── Request (درخواست) ────────────────────────────────────────────────────────


class Request(AgencyOwned):
    """
    A buyer/renter need registered by an agent on behalf of a client (مراجعه‌کننده).

    contact FK links to the structured Contact.
    property_types is stored as JSON list of PropertyType values.
    Budget is in Tomans (BigIntegerField).
    expires_at defaults to 60 days from creation.
    """

    # --- Client info ---
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requests",
        verbose_name=_("مخاطب"),
    )
    # Legacy plain-text fields (for backwards compat and quick entry)
    client_name = models.CharField(_("نام مراجعه‌کننده"), max_length=200)
    client_phone = EncryptedCharField(
        _("شماره مراجعه‌کننده"), max_length=255, blank=True
    )
    source = models.CharField(
        _("منبع مراجعه"),
        max_length=20,
        choices=RequestSource.choices,
        default=RequestSource.WALK_IN,
    )

    # --- Need specification ---
    deal_type = models.CharField(
        _("نوع معامله"),
        max_length=20,
        choices=DealType.choices,
        default=DealType.SALE,
        db_index=True,
    )
    # JSON list of PropertyType values, e.g. ["apartment", "villa"]
    property_types = models.JSONField(
        _("نوع ملک موردنظر"),
        default=list,
        blank=True,
    )
    min_area = models.PositiveIntegerField(_("حداقل متراژ"), null=True, blank=True)
    max_area = models.PositiveIntegerField(_("حداکثر متراژ"), null=True, blank=True)
    min_rooms = models.PositiveSmallIntegerField(
        _("حداقل اتاق"), null=True, blank=True
    )
    max_rooms = models.PositiveSmallIntegerField(
        _("حداکثر اتاق"), null=True, blank=True
    )
    city = models.CharField(_("شهر"), max_length=100, blank=True, db_index=True)
    district = models.CharField(_("منطقه / محله"), max_length=200, blank=True)
    min_budget = models.BigIntegerField(
        _("حداقل بودجه (تومان)"), null=True, blank=True
    )
    max_budget = models.BigIntegerField(
        _("حداکثر بودجه (تومان)"), null=True, blank=True
    )
    notes = models.TextField(_("توضیحات"), blank=True)

    # --- Workflow ---
    status = models.CharField(
        _("وضعیت"),
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.NEW,
        db_index=True,
    )
    priority = models.CharField(
        _("اولویت"),
        max_length=10,
        choices=RequestPriority.choices,
        default=RequestPriority.NORMAL,
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_requests",
        verbose_name=_("مشاور مسئول"),
    )

    # --- Dates ---
    expires_at = models.DateTimeField(
        _("تاریخ انقضا"),
        null=True,
        blank=True,
        help_text=_("پیش‌فرض ۶۰ روز از ایجاد"),
    )
    contacted_at = models.DateTimeField(_("آخرین تماس"), null=True, blank=True)
    closed_at = models.DateTimeField(_("تاریخ بستن"), null=True, blank=True)

    class Meta:
        verbose_name = _("درخواست")
        verbose_name_plural = _("درخواست‌ها")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "status"]),
            models.Index(fields=["agency", "deal_type"]),
            models.Index(fields=["agency", "priority", "status"]),
            models.Index(fields=["contact"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.client_name} — "
            f"{self.get_deal_type_display()} ({self.get_status_display()})"
        )

    def save(self, *args, **kwargs) -> None:
        """Auto-set expires_at to 60 days if not provided."""
        if not self.expires_at and not self.pk:
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(days=60)
        super().save(*args, **kwargs)
