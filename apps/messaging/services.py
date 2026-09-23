from django.conf import settings
from django.db import transaction
from django.utils import timezone
from apps.messaging import rendering
from apps.messaging.models import SMSMessage, SMSProviderConfig, SMSPurpose, SMSStatus, SMSTemplate
from apps.messaging.providers import DeliveryState, SMSProvider, SMSProviderError, build_provider, mask_phone
from apps.messaging.segments import count_segments

import logging
from datetime import timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)

_PERSIAN_TO_ASCII = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
STATUS_POLL_WINDOW = timedelta(hours=48)

def normalize_mobile(phone: str) -> str:
    p = (phone or "").strip().translate(_PERSIAN_TO_ASCII)
    p = "".join(ch for ch in p if ch.isdigit() or ch == "+")
    if p.startswith("+98"): p = "0" + p[3:]
    elif p.startswith("0098"): p = "0" + p[4:]
    elif p.startswith("98") and len(p) == 12: p = "0" + p[2:]
    elif p.startswith("9") and len(p) == 10: p = "0" + p
    if not (len(p) == 11 and p.startswith("09") and p.isdigit()):
        raise ValueError("شماره موبایل معتبر نیست")
    return p

def get_agency_config(agency) -> SMSProviderConfig | None:
    if agency is None: return None
    return SMSProviderConfig.all_objects.filter(agency=agency, is_active=True).first()

def provider_for_config(config: SMSProviderConfig | None) -> tuple[str, SMSProvider]:
    if config is not None:
        return config.provider, build_provider(config.provider, **config.credentials())
    return platform_provider(getattr(settings, "SMS_DEFAULT_PROVIDER", "console"))

def platform_provider(name: str) -> tuple[str, SMSProvider]:
    creds = getattr(settings, "SMS_PLATFORM_CREDENTIALS", {}).get(name, {})
    return name, build_provider(name, **creds)

def build_context(agency=None, contact=None, listing=None, extra: dict | None = None) -> dict:
    ctx: dict[str, object] = {}
    if agency is not None:
        ctx["نام_آژانس"] = agency.name
        ctx["تلفن_آژانس"] = agency.phone or ""
    if contact is not None:
        ctx["نام"] = contact.full_name
    if listing is not None:
        ctx["کد_فایل"] = getattr(listing, "code", "") or ""
        get_type = getattr(listing, "get_property_type_display", None)
        ctx["نوع_ملک"] = get_type() if callable(get_type) else ""
        hood = getattr(listing, "neighborhood", None)
        ctx["محله"] = str(hood) if hood else (getattr(listing, "district", "") or "")
    if extra: ctx.update(extra)
    return ctx

def preview(body: str, context: dict | None = None) -> dict:
    text = rendering.render(body, context if context is not None else rendering.sample_context())
    seg = count_segments(text)
    return {"text": text, "length": seg.length, "parts": seg.parts, "per_part": seg.per_part, "remaining": seg.remaining, "encoding": seg.encoding, "is_persian": seg.is_persian, "unknown": rendering.unknown_placeholders(body)}

def queue_sms(*, agency, to: str, body: str, purpose: str = SMSPurpose.MANUAL, contact=None, template: SMSTemplate | None = None, user=None, dispatch: bool = True) -> SMSMessage:
    phone = normalize_mobile(to)
    body = (body or "").strip()
    if not body: raise ValueError("متن پیامک خالی است")
    config = get_agency_config(agency)
    default_name = getattr(settings, "SMS_DEFAULT_PROVIDER", "console")
    provider_name = config.provider if config else default_name
    seg = count_segments(body)
    msg = SMSMessage.all_objects.create(
        agency=agency, contact=contact, template=template,
        created_by=user if getattr(user, "is_authenticated", False) else None,
        purpose=purpose, recipient=phone, recipient_last4=phone[-4:],
        body=body, segments=seg.parts, encoding=seg.encoding,
        provider=provider_name, status=SMSStatus.QUEUED)
    logger.info("sms queued id=%s to=%s parts=%s", msg.pk, mask_phone(phone), seg.parts)
    if dispatch:
        from apps.messaging.tasks import send_sms_task
        transaction.on_commit(lambda: send_sms_task.delay(msg.pk))
    return msg

def send_to_contact(*, agency, contact, body: str, user=None, template=None, listing=None) -> SMSMessage:
    phone = contact.phone or contact.phone_normalized
    if not phone: raise ValueError("این مخاطب شماره موبایل ندارد")
    text = rendering.render(body, build_context(agency, contact, listing))
    return queue_sms(agency=agency, to=phone, body=text, purpose=SMSPurpose.MANUAL, contact=contact, template=template, user=user)

def deliver_message(message_id: int) -> SMSMessage:
    with transaction.atomic():
        msg = SMSMessage.all_objects.select_for_update().get(pk=message_id)
        if msg.status != SMSStatus.QUEUED: return msg
        msg.attempts += 1
        msg.save(update_fields=["attempts", "updated_at"])