"""
Messaging app models — Phase 4A + 4B

Models:
- AgencySMSConfig  : per-agency SMS provider config (encrypted API key)
- SMSTemplate      : message templates with variable placeholders
- SMSMessage       : log of every sent/queued message with state machine
"""

from __future__ import annotations

import re

from django.core import signing
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import EncryptedCharField
from apps.core.models import AgencyOwned, TimeStampedModel

# ─── Choices ──────────────────────────────────────────────────────────────────

TEMPLATE_VARIABLES = [
    "{نام}",
    "{نام_آژانس}",
    "{تلفن_آژانس}",
    "{کد_فایل}",
    "{نوع_ملک}",
    "{محله}",
]

# Farsi / Arabic characters use UCS-2 (70 chars/segment); Latin uses GSM-7 (160/segment).
_FARSI_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
_UCS2_SEGMENT = 70
_UCS2_MULTI = 67
_GSM7_SEGMENT = 160
_GSM7_MULTI = 153


def sms_segment_count(text: str) -> int:
    """Return the number of SMS segments for the given text."""
    if _FARSI_RE.search(text):
        # UCS-2 encoding
        limit1, limit_n = _UCS2_SEGMENT, _UCS2_MULTI
    else:
        limit1, limit_n = _GSM7_SEGMENT, _GSM7_MULTI
    n = len(text)
    if n <= limit1:
        return 1
    return -(-n // limit_n)  # ceiling division


class SMSProvider(models.TextChoices):
    KAVENEGAR = "kavenegar", _("کاوه‌نگار")
    MELIPAYAMAK = "melipayamak", _("ملی‌پیامک")
    CONSOLE = "console", _("کنسول (توسعه)")


class SMSMessageState(models.TextChoices):
    QUEUED = "queued", _("صف")
    SENT = "sent", _("ارسال‌شده")
    DELIVERED = "delivered", _("تحویل‌شده")
    FAILED = "failed", _("ناموفق")


# ─── AgencySMSConfig ──────────────────────────────────────────────────────────


class AgencySMSConfig(AgencyOwned, TimeStampedModel):
    """
    Per-agency SMS provider configuration.

    API keys are encrypted at rest using EncryptedCharField.
    Only the last 4 digits of the sender line are stored in logs.
    """

    provider = models.CharField(
        _("ارائه‌دهنده"),
        max_length=20,
        choices=SMSProvider.choices,
        default=SMSProvider.CONSOLE,
    )
    # Kavenegar: API key; MeliPayamak: username — stored encrypted
    api_key = EncryptedCharField(
        _("کلید API / نام کاربری"),
        blank=True,
        help_text=_("رمزنگاری‌شده در پایگاه داده"),
    )
    # MeliPayamak: password (optional for Kavenegar)
    api_secret = EncryptedCharField(
        _("رمز عبور / secret"),
        blank=True,
        help_text=_("رمزنگاری‌شده در پایگاه داده"),
    )
    sender_line = models.CharField(
        _("شماره خط"),
        max_length=20,
        blank=True,
        help_text=_("شماره فرستنده (خدماتی یا تبلیغاتی)"),
    )
    is_active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("تنظیمات پیامک آژانس")
        verbose_name_plural = _("تنظیمات پیامک آژانس‌ها")

    def __str__(self) -> str:
        return f"{self.agency} — {self.get_provider_display()}"

    def get_provider_instance(self):
        """Instantiate and return the correct SMSProvider adapter."""
        from apps.messaging.providers.console import ConsoleSMSProvider
        from apps.messaging.providers.kavenegar import KavenegarSMSProvider
        from apps.messaging.providers.melipayamak import MeliPayamakSMSProvider

        if self.provider == SMSProvider.KAVENEGAR:
            return KavenegarSMSProvider(
                api_key=self.api_key or "",
                sender=self.sender_line,
            )
        if self.provider == SMSProvider.MELIPAYAMAK:
            return MeliPayamakSMSProvider(
                username=self.api_key or "",
                password=self.api_secret or "",
                sender=self.sender_line,
            )
        return ConsoleSMSProvider()


# ─── SMSTemplate ──────────────────────────────────────────────────────────────


class SMSTemplate(AgencyOwned, TimeStampedModel):
    """
    Reusable message template with variable placeholders.

    Variables: {نام}, {نام_آژانس}, {تلفن_آژانس}, {کد_فایل}, {نوع_ملک}, {محله}
    """

    name = models.CharField(_("نام قالب"), max_length=100)
    body = models.TextField(
        _("متن قالب"),
        help_text=_(
            "متغیرهای مجاز: {نام}, {نام_آژانس}, {تلفن_آژانس}, {کد_فایل}, {نوع_ملک}, {محله}"
        ),
    )
    is_active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("قالب پیامک")
        verbose_name_plural = _("قالب‌های پیامک")
        unique_together = [("agency", "name")]
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.agency} — {self.name}"

    def render(self, context: dict[str, str]) -> str:
        """Substitute placeholders with context values."""
        text = self.body
        for key, value in context.items():
            text = text.replace(f"{{{key}}}", value)
        return text

    @property
    def segment_count_estimate(self) -> int:
        """Segment count for the raw template (no substitutions)."""
        return sms_segment_count(self.body)


# ─── SMSMessage ───────────────────────────────────────────────────────────────


class SMSMessage(AgencyOwned, TimeStampedModel):
    """
    Immutable log record for every SMS message.

    State machine:
      queued → sent → delivered
                   ↘ failed

    recipient_masked: last 4 digits only — never store full number in log.
    """

    template = models.ForeignKey(
        SMSTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
        verbose_name=_("قالب"),
    )
    # Recipient — only last 4 digits for GDPR/privacy
    recipient_masked = models.CharField(
        _("گیرنده (آخر ۴ رقم)"),
        max_length=10,
    )
    body = models.TextField(_("متن پیامک"))
    state = models.CharField(
        _("وضعیت"),
        max_length=20,
        choices=SMSMessageState.choices,
        default=SMSMessageState.QUEUED,
        db_index=True,
    )
    provider = models.CharField(
        _("ارائه‌دهنده"),
        max_length=20,
        choices=SMSProvider.choices,
        blank=True,
    )
    provider_message_id = models.CharField(
        _("شناسه پیامک نزد ارائه‌دهنده"),
        max_length=100,
        blank=True,
    )
    # Delivery metadata
    sent_at = models.DateTimeField(_("زمان ارسال"), null=True, blank=True)
    delivered_at = models.DateTimeField(_("زمان تحویل"), null=True, blank=True)
    failed_at = models.DateTimeField(_("زمان شکست"), null=True, blank=True)
    failure_reason = models.CharField(_("دلیل شکست"), max_length=255, blank=True)
    # Cost tracking
    cost = models.DecimalField(_("هزینه"), max_digits=12, decimal_places=2, default=0)
    segment_count = models.PositiveSmallIntegerField(_("تعداد بخش"), default=1)

    # Optional FK to contact for CRM tracing
    contact = models.ForeignKey(
        "crm.Contact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sms_messages",
        verbose_name=_("مخاطب"),
    )

    class Meta:
        verbose_name = _("پیامک")
        verbose_name_plural = _("پیامک‌ها")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "state"]),
            models.Index(fields=["agency", "created_at"]),
            models.Index(fields=["contact", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"SMS #{self.pk} → {self.recipient_masked} [{self.state}]"


# ─── Phase 4B ─────────────────────────────────────────────────────────────────


class AgencySMSPolicy(AgencyOwned, TimeStampedModel):
    """
    Per-agency auto-send policy for match notifications.

    Controls:
    - auto_send_exact / auto_send_strong: send automatically for high-score matches
    - score_threshold: minimum score to trigger auto-send (default 70)
    - quiet_start / quiet_end: local hours (Asia/Tehran) during which SMS is suppressed
    - daily_cap: max SMS per contact per day (dedup guard)
    - is_active: master switch
    """

    is_active = models.BooleanField(_("فعال"), default=True)
    auto_send_exact = models.BooleanField(
        _("ارسال خودکار برای تطبیق دقیق"),
        default=True,
        help_text=_("برای تطبیق‌های با امتیاز ≥ score_threshold خودکار پیامک بفرست"),
    )
    auto_send_strong = models.BooleanField(
        _("ارسال خودکار برای تطبیق قوی"),
        default=True,
        help_text=_("برای تطبیق‌های با امتیاز ≥ 50 خودکار پیامک بفرست"),
    )
    score_threshold = models.PositiveSmallIntegerField(
        _("آستانه امتیاز ارسال خودکار"),
        default=70,
    )
    quiet_start = models.PositiveSmallIntegerField(
        _("ساعت شروع سکوت (0–23)"),
        default=22,
        help_text=_("از این ساعت پیامک نفرست"),
    )
    quiet_end = models.PositiveSmallIntegerField(
        _("ساعت پایان سکوت (0–23)"),
        default=8,
        help_text=_("تا این ساعت پیامک نفرست"),
    )
    daily_cap = models.PositiveSmallIntegerField(
        _("سقف روزانه به ازای هر مخاطب"),
        default=2,
    )
    match_template = models.ForeignKey(
        SMSTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("قالب پیامک تطبیق"),
    )

    class Meta:
        verbose_name = _("سیاست پیامک آژانس")
        verbose_name_plural = _("سیاست‌های پیامک آژانس‌ها")

    def __str__(self) -> str:
        return f"SMSPolicy({self.agency})"


class MatchSMSSent(TimeStampedModel):
    """
    Deduplication guard: records that an SMS was sent for a (listing, request) pair.

    Prevents sending duplicate SMS for the same match regardless of how many times
    the matching engine runs.
    """

    agency = models.ForeignKey(
        "agencies.Agency",
        on_delete=models.CASCADE,
        related_name="match_sms_sent",
        db_index=True,
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="match_sms_sent",
    )
    request = models.ForeignKey(
        "crm.Request",
        on_delete=models.CASCADE,
        related_name="match_sms_sent",
    )
    sms = models.ForeignKey(
        SMSMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="match_sent",
    )

    class Meta:
        verbose_name = _("پیامک تطبیق ارسال‌شده")
        verbose_name_plural = _("پیامک‌های تطبیق ارسال‌شده")
        unique_together = [("listing", "request")]
        indexes = [
            models.Index(fields=["agency", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"MatchSMSSent listing={self.listing_id} req={self.request_id}"


# ─── Unsubscribe / renewal token helpers ─────────────────────────────────────

_TOKEN_SALT = "messaging:unsubscribe"  # noqa: S105
_RENEWAL_SALT = "messaging:renewal"  # noqa: S105
_TOKEN_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def make_unsubscribe_token(contact_id: int) -> str:
    """Return a signed Django token that can be verified to revoke consent."""
    return signing.dumps({"contact_id": contact_id}, salt=_TOKEN_SALT)


def verify_unsubscribe_token(token: str) -> int | None:
    """Verify the token and return contact_id, or None if invalid/expired."""
    try:
        data = signing.loads(token, salt=_TOKEN_SALT, max_age=_TOKEN_MAX_AGE)
        return int(data["contact_id"])
    except (signing.BadSignature, signing.SignatureExpired, KeyError, ValueError):
        return None


def make_renewal_token(request_id: int) -> str:
    """Return a signed token to renew or stop a CRM Request."""
    return signing.dumps({"request_id": request_id}, salt=_RENEWAL_SALT)


def verify_renewal_token(token: str) -> int | None:
    """Verify the renewal token and return request_id, or None if invalid/expired."""
    try:
        data = signing.loads(token, salt=_RENEWAL_SALT, max_age=_TOKEN_MAX_AGE)
        return int(data["request_id"])
    except (signing.BadSignature, signing.SignatureExpired, KeyError, ValueError):
        return None
