"""Messaging models (phase 4A): SMS provider config, templates, and the SMS log.

- SMSProviderConfig: one per agency; secrets encrypted at rest (EncryptedCharField).
- SMSTemplate: agency templates with Persian placeholders ({نام}, {کد_فایل}, ...).
- SMSMessage: every outgoing SMS with a strict state machine:

      queued ──► sending ──► sent ──► delivered
         │          │          │
         │          ├──► queued (retry)
         └──────────┴──────────┴──► failed

  The recipient number is stored encrypted; only the last 4 digits are kept
  in clear (recipient_last4) for the log UI and log lines.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.fields import EncryptedCharField
from apps.core.models import AgencyManager, AgencyOwned, TimeStampedModel, UnfilteredAgencyManager

# ─── Choices ──────────────────────────────────────────────────────────────────


class ProviderName(models.TextChoices):
    KAVENEGAR = \"kavenegar\", _(\"کاوه‌نگار\")
    MELIPAYAMAK = \"melipayamak\", _(\"ملی‌پیامک\")
    CONSOLE = \"console\", _(\"کنسول (توسعه)\")
    FAKE = \"fake\", _(\"Fake (تست)\")


class SMSStatus(models.TextChoices):
    QUEUED = \"queued\", _(\"در صف\")
    SENDING = \"sending\", _(\"در حال ارسال\")
    SENT = \"sent\", _(\"ارسال‌شده\")
    DELIVERED = \"delivered\", _(\"تحویل‌شده\")
    FAILED = \"failed\", _(\"ناموفق\")


class SMSPurpose(models.TextChoices):
    MANUAL = \"manual\", _(\"ارسال دستی\")
    OTP = \"otp\", _(\"کد ورود\")
    MATCH = \"match\", _(\"اطلاع تطبیق\")
    SYSTEM = \"system\", _(\"سیستمی\")
    TEST = \"test\", _(\"آزمایشی\")


# Allowed transitions of the SMSMessage state machine.
TRANSITIONS: dict[str, set[str]] = {
    SMSStatus.QUEUED: {SMSStatus.SENDING, SMSStatus.FAILED},
    SMSStatus.SENDING: {SMSStatus.SENT, SMSStatus.QUEUED, SMSStatus.FAILED, SMSStatus.DELIVERED},
    SMSStatus.SENT: {SMSStatus.DELIVERED, SMSStatus.FAILED},
    SMSStatus.DELIVERED: set(),
    SMSStatus.FAILED: set(),
}


class InvalidSMSTransition(Exception):
    \"\"\"Raised when a status change is not allowed by TRANSITIONS.\"\"\"


# ─── Provider config ──────────────────────────────────────────────────────────


class SMSProviderConfig(AgencyOwned):
    \"\"\"SMS panel settings of one agency.\"\"\"

    provider = models.CharField(
        _(\"ارائه‌دهنده\"),
        max_length=20,
        choices=ProviderName.choices,
        default=ProviderName.CONSOLE,
    )
    api_key = EncryptedCharField(_(\"کلید API\"), max_length=500, blank=True)
    username = models.CharField(_(\"نام کاربری پنل\"), max_length=100, blank=True)
    password = EncryptedCharField(_(\"رمز پنل\"), max_length=500, blank=True)
    sender_line = models.CharField(_(\"شماره خط\"), max_length=20, blank=True)
    is_active = models.BooleanField(_(\"فعال\"), default=True)
    last_balance = models.DecimalField(
        _(\"آخرین اعتبار\"), max_digits=18, decimal_places=2, null=True, blank=True
    )
    balance_unit = models.CharField(_(\"واحد اعتبار\"), max_length=10, blank=True)
    balance_checked_at = models.DateTimeField(_(\"زمان بررسی اعتبار\"), null=True, blank=True)
    last_test_ok = models.BooleanField(_(\"آخرین تست موفق\"), null=True, blank=True)
    last_test_error = models.CharField(_(\"خطای آخرین تست\"), max_length=300, blank=True)

    class Meta:
        verbose_name = _(\"تنظیمات پنل پیامک\")
        verbose_name_plural = _(\"تنظیمات پنل‌های پیامک\")
        constraints = [
            models.UniqueConstraint(fields=[\"agency\"], name=\"messaging_one_sms_config_per_agency\"),
        ]

    def __str__(self) -> str:
        return f\"{self.agency} — {self.get_provider_display()}\"

    def credentials(self) -> dict:
        \"\"\"Kwargs for providers.build_provider (never log this dict).\"\"\"
        return {
            \"api_key\": self.api_key or \"\",
            \"username\": self.username or \"\",
            \"password\": self.password or \"\",
            \"sender\": self.sender_line or \"\",
        }


# ─── Templates ────────────────────────────────────────────────────────────────


class SMSTemplate(AgencyOwned):
    \"\"\"Reusable SMS text with placeholders.\"\"\"

    name = models.CharField(_(\"نام قالب\"), max_length=100)
    key = models.SlugField(_(\"کلید\"), max_length=50, help_text=_(\"شناسه لاتین، مثلاً match_found\"))
    body = models.TextField(_(\"متن\"))
    is_active = models.BooleanField(_(\"فعال\"), default=True)

    class Meta:
        verbose_name = _(\"قالب پیامک\")
        verbose_name_plural = _(\"قالب‌های پیامک\")
        ordering = [\"name\"]
        constraints = [
            models.UniqueConstraint(
                fields=[\"agency\", \"key\"], name=\"messaging_template_key_per_agency\"
            ),
        ]

    def __str__(self) -> str:
        return self.name


# ─── SMS log ──────────────────────────────────────────────────────────────────


class SMSMessage(TimeStampedModel):
    \"\"\"
    One outgoing SMS. agency is nullable only for platform messages (OTP before
    the user belongs to an agency); tenant filtering still applies via AgencyManager.
    \"\"\"

    agency = models.ForeignKey(
        \"agencies.Agency\",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name=\"sms_messages\",
        verbose_name=_(\"آژانس\"),
    )
    contact = models.ForeignKey(
        \"crm.Contact\",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=\"sms_messages\",
        verbose_name=_(\"مخاطب\"),
    )
    template = models.ForeignKey(
        SMSTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=\"messages\",
        verbose_name=_(\"قالب\"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=\"sent_sms\",
        verbose_name=_(\"ارسال‌کننده\"),
    )
    purpose = models.CharField(
        _(\"نوع\"), max_length=10, choices=SMSPurpose.choices, default=SMSPurpose.MANUAL
    )
    recipient = EncryptedCharField(_(\"گیرنده\"), max_length=255)
    recipient_last4 = models.CharField(_(\"۴ رقم آخر گیرنده\"), max_length=4, blank=True)
    body = models.TextField(_(\"متن\"))
    segments = models.PositiveSmallIntegerField(_(\"تعداد بخش\"), default=1)
    encoding = models.CharField(_(\"کدگذاری\"), max_length=5, blank=True)
    provider = models.CharField(_(\"ارائه‌دهنده\"), max_length=20, choices=ProviderName.choices)
    provider_message_id = models.CharField(
        _(\"شناسه ارائه‌دهنده\"), max_length=64, blank=True, db_index=True
    )
    status = models.CharField(
        _(\"وضعیت\"),
        max_length=10,
        choices=SMSStatus.choices,
        default=SMSStatus.QUEUED,
        db_index=True,
    )
    provider_status = models.CharField(_(\"وضعیت خام ارائه‌دهنده\"), max_length=50, blank=True)
    cost_rial = models.PositiveIntegerField(_(\"هزینه (ریال)\"), null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(_(\"تعداد تلاش\"), default=0)
    error_message = models.CharField(_(\"خطا\"), max_length=300, blank=True)
    scheduled_at = models.DateTimeField(_(\"زمان برنامه‌ریزی\"), null=True, blank=True)
    sent_at = models.DateTimeField(_(\"زمان ارسال\"), null=True, blank=True)
    delivered_at = models.DateTimeField(_(\"زمان تحویل\"), null=True, blank=True)
    failed_at = models.DateTimeField(_(\"زمان شکست\"), null=True, blank=True)

    objects = AgencyManager()
    all_objects = UnfilteredAgencyManager()

    class Meta:
        verbose_name = _(\"پیامک\")
        verbose_name_plural = _(\"لاگ پیامک‌ها\")
        ordering = [\" -created_at\"]
        indexes = [
            models.Index(
                fields=[\"agency\", \"status\", \"created_at\"], name=\"messaging_s_agency__st_idx\"
            ),
            models.Index(
                fields=[\"agency\", \"contact\", \"created_at\"], name=\"messaging_s_agency__ct_idx\"
            ),
            models.Index(fields=[\"status\", \"sent_at\"], name=\"messaging_s_status_sent_idx\"),
        ]

    def __str__(self) -> str:
        return f\"پیامک به ***{self.recipient_last4} ({self.get_status_display()})\"

    # ── State machine ────────────────────────────────────────────────────────

    def can_transition(self, new_status: str) -> bool:
        return new_status in TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status: str, *, error: str = \"\", save: bool = True) -> None:
        \"\"\"Move to ``new_status`` or raise InvalidSMSTransition.\"\"\"
        if new_status == self.status:
            return
        if not self.can_transition(new_status):
            raise InvalidSMSTransition(f\"{self.status} → {new_status}\")
        now = timezone.now()
        self.status = new_status
        fields = [\"status\", \"updated_at\"]
        if new_status == SMSStatus.SENT:
            self.sent_at = now
            fields.append(\"sent_at\")
        elif new_status == SMSStatus.DELIVERED:
            self.delivered_at = now
            fields.append(\"delivered_at\")
            if not self.sent_at:
                self.sent_at = now
                fields.append(\"sent_at\")
        elif new_status == SMSStatus.FAILED:
            self.failed_at = now
            self.error_message = (error or self.error_message)[:300]
            fields += [\"failed_at\", \"error_message\"]
        elif new_status == SMSStatus.QUEUED and error:
            self.error_message = error[:300]
            fields.append(\"error_message\")
        if save and self.pk:
            self.save(update_fields=fields)

    @property
    def is_final(self) -> bool:
        return self.status in (SMSStatus.DELIVERED, SMSStatus.FAILED)"