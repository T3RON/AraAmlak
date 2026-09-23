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
    TEST = \"test\", _(\"آزمایشی\")"