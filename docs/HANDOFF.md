# HANDOFF — آرا املاک / Ara Amlak

**آخرین به‌روزرسانی:** پس از تکمیل فازهای 4A + 4B — زیرساخت پیامک و سیاست اعلان
**شاخه جاری:** `phase/4ab-sms-notification`
**آخرین کامیت:** `11e89f5` feat(messaging): Phase 4A+4B

---

## ۱. فاز جاری و پیشرفت

| فاز | موضوع | وضعیت | درصد |
|-----|--------|--------|------|
| 0A | زیرساخت (Docker, CI, pre-commit) | ✅ کامل | 100% |
| 0B | دیزاین‌سیستم Apple-style | ⚠️ نسبی | 60% |
| 0C | هویت کاربر، نقش‌ها، AuditLog، دعوت عضو | ✅ کامل | 100% |
| 1A | مدل داده فایل (City/Neighborhood/Feature) | ✅ کامل | 100% |
| 1B | صفحات CRUD فایل | ✅ کامل | 100% |
| 1C | رسانه (آپلود، پردازش، سند خصوصی) | ✅ کامل | 100% |
| 1D | جستجو، فیلتر، normalize_fa، ImportJob | ✅ کامل | 100% |
| 2A | مخاطبین، درخواست‌ها، رضایت پیامک | ✅ کامل | 100% |
| 2B | تایم‌لاین، بازدید، وظایف، اعلان‌ها | ✅ کامل | 100% |
| 3 | Matching engine + Dashboard | ✅ کامل | 100% |
| 4 (publishing) | Publishing به پورتال‌ها | ✅ کامل | 100% |
| **4A** | **زیرساخت پیامک (Kavenegar, MeliPayamak, Console)** | **✅ کامل** | **100%** |
| **4B** | **ارسال خودکار تطبیق، فرم عمومی، لغو، تمدید** | **✅ کامل** | **100%** |
| 5–11 | صدا، رندر، انتشار، حسابداری، AI، ... | ⬜ شروع نشده | 0% |

---

## ۲. آنچه در این جلسه کامل شد

### فاز 4A — زیرساخت پیامک

- **[`apps/messaging/providers/base.py`](../apps/messaging/providers/base.py)** — `SMSProvider` ABC
- **[`apps/messaging/providers/console.py`](../apps/messaging/providers/console.py)** — dev/test adapter
- **[`apps/messaging/providers/kavenegar.py`](../apps/messaging/providers/kavenegar.py)** — Kavenegar REST adapter
- **[`apps/messaging/providers/melipayamak.py`](../apps/messaging/providers/melipayamak.py)** — MeliPayamak REST adapter
- **[`apps/messaging/models.py`](../apps/messaging/models.py)** — `AgencySMSConfig`, `SMSTemplate`, `SMSMessage` (state machine)
- **[`apps/messaging/services.py`](../apps/messaging/services.py)** — `enqueue_sms`, `send_sms_message`, `get_provider_for_agency`
- **[`apps/messaging/tasks.py`](../apps/messaging/tasks.py)** — `send_sms_task` با exponential backoff
- **[`apps/accounts/tasks.py`](../apps/accounts/tasks.py)** — OTP task حالا ConsoleSMSProvider واقعی را صدا می‌زند
- Migration: `messaging/0001_initial`

### فاز 4B — ارسال خودکار و فرم عمومی

- **[`apps/messaging/models.py`](../apps/messaging/models.py)** — `AgencySMSPolicy` (ساعت سکوت، سقف روزانه، آستانه امتیاز)، `MatchSMSSent` (dedup)، `make/verify_unsubscribe_token`، `make/verify_renewal_token`
- **[`apps/messaging/notification_policy.py`](../apps/messaging/notification_policy.py)** — `should_send_sms()` (تابع خالص)، `process_match_notification()`، `handle_unsubscribe()`، `handle_renewal()`، `send_renewal_sms()`
- **[`apps/messaging/views.py`](../apps/messaging/views.py)** — `PublicSubscribeView` (دو مرحله‌ای: OTP)، `UnsubscribeView`، `RenewalView`
- **[`apps/messaging/urls.py`](../apps/messaging/urls.py)** — `/messaging/subscribe/<slug>/`، `/messaging/unsubscribe/<token>/`، `/messaging/renew/<token>/<action>/`
- **[`apps/matching/tasks.py`](../apps/matching/tasks.py)** — پس از یافتن تطبیق‌ها، `process_match_notification` صدا می‌زند
- Beat task: `send_renewal_reminders` روزانه ساعت ۹
- Templates: public_subscribe, verify, done, unsubscribe, renewal
- Migration: `messaging/0002_agencysmspolicy_matchsmssent`
- **53 تست** در `tests/test_4ab_sms_notification.py` (مجموعاً ۲۷۱ تست)

---

## ۳. تست‌ها (271 passing — بدون PostGIS)

| فایل | تعداد |
|------|-------|
| `tests/test_otp.py` | 9 |
| `tests/test_listings_nogis.py` | 10 |
| `tests/test_crm_nogis.py` | 8 |
| `tests/test_matching_nogis.py` | 13 |
| `tests/test_publishing_nogis.py` | 12 |
| `tests/test_core_currency.py` | 16 |
| `tests/test_encrypted_field.py` | 4 |
| `tests/test_0c_roles_audit_invite.py` | 18 |
| `tests/test_1a_geo_models.py` | 16 |
| `tests/test_2a_contact_consent.py` | 16 |
| `tests/test_1c_media.py` | 19 |
| `tests/test_1d_search_import.py` | 38 |
| `tests/test_2b_timeline_visit_tasks.py` | 26 |
| `tests/test_4ab_sms_notification.py` | **53** |
| **جمع** | **271** |

---

## ۴. آنچه نیمه‌کاره است

### ۴.۱ فازهای بعدی (اولویت‌بندی)
1. **5A** — صدا و ثبت هوشمند (MVP اصلی پروژه — Whisper/Gemini)
2. **5B** — پیش‌نویس هوشمند فایل از صدا
3. **6A** — رندر پوستر (PDF, Pillow)
4. **7A** — انتشار واقعی به پورتال‌ها

### ۴.۲ موارد نیمه‌کاره
- `test_tenant_isolation.py` — تست‌های pre-existing broken
- `test_health.py` — pre-existing broken
- پنل مدیریت SMS (AgencySMSConfig) فعلاً فقط از طریق admin
- OTP در تولید باید از `AgencySMSConfig` آژانس استفاده کند (فعلاً Console)
- `openpyxl` برای xlsx import نیاز به نصب جداگانه دارد

---

## ۵. تله‌ها و نکته‌های محیطی

| موضوع | جزئیات |
|--------|---------|
| **Python** | 3.13.0 |
| **Django** | 5.2 LTS |
| **GDAL** | روی Windows نصب نیست |
| **Fernet key** | `_Rb6cmq4gjE2pZRi7BalzwZb49Amh9s0NGmxP0dbyW4=` |
| **SMS Provider** | `AgencySMSConfig` با `is_active=True` باید وجود داشته باشد؛ وگرنه Console |
| **ConsentRecord.is_active** | property است، نه فیلد DB — در filter از `revoked_at__isnull=True` استفاده کنید |
| **RequestStatus** | مقادیر: `new`, `in_progress`, `matched`, `closed`, `cancelled`, `expired` — `active` وجود ندارد |
| **Request.expires_at** | `DateTimeField` است نه `DateField` |
| **ContactPhone** | فیلدهای `phone` (encrypted) و `phone_normalized` دارد — `phone_raw` وجود ندارد |
| **ConsentRecord** | به `agency` FK نیاز دارد؛ فیلد `text_version` (نه `consent_text_version`) |
| **URL پیشوند SMS** | `/messaging/` |
| **dev server** | `python manage.py runserver 8070 --settings=ara_amlak.settings.local_sqlite` |

---

## ۶. وضعیت گیت

- شاخه: `phase/4ab-sms-notification` (از `phase/2b-timeline-visits-tasks`)
- آخرین کامیت: `11e89f5`
- پوش شده: ✅

---

## ۷. قدم‌های بعدی به ترتیب

1. فاز 5A — Voice entry (Whisper/Gemini) + ثبت هوشمند فایل
2. فاز 5B — پیش‌نویس هوشمند
3. فاز 6A — رندر PDF پوستر
4. فاز 7A — انتشار واقعی به پورتال‌ها

---

## ۸. دستورهای اجرا و تست

```powershell
# تست no-GIS (271 تست)
python -m pytest --ds=ara_amlak.settings.testing_nogis tests/ `
  --ignore=tests/test_tenant_isolation.py `
  --ignore=tests/test_health.py -v

# lint
ruff check .

# dev server (port 8070)
python manage.py runserver 8070 --settings=ara_amlak.settings.local_sqlite
# login: 09000000000 / admin1234
```

---

*این فایل را در ابتدای هر جلسه بخوان. قبل از شروع کد، `git status` و آخرین تست را اجرا کن.*
