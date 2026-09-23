# HANDOFF — آرا املاک / Ara Amlak

**آخرین به‌روزرسانی:** پس از تکمیل فاز 2B — تایم‌لاین، بازدید، وظایف، اعلان‌ها
**شاخه جاری:** `phase/2b-timeline-visit-tasks`
**آخرین کامیت:** (پس از کامیت این فایل پر می‌شود)

---

## ۱. فاز جاری و پیشرفت

| فاز | موضوع | وضعیت | درصد |
|-----|--------|--------|------|
| 0a | زیرساخت (Docker, CI, pre-commit) | ✅ کامل | 100% |
| 0B | دیزاین‌سیستم Apple-style | ⚠️ نسبی | 60% |
| 0C | هویت کاربر، نقش‌ها، AuditLog، دعوت عضو | ✅ کامل | 100% |
| 1A | مدل داده فایل (City/Neighborhood/Feature) | ✅ کامل | 100% |
| 1B | صفحات CRUD فایل | ✅ کامل | 100% |
| 1C | رسانه (آپلود، پردازش، سند خصوصی) | ✅ کامل | 100% |
| 1D | جستجو، فیلتر، normalize_fa، ImportJob | ✅ کامل | 100% |
| 2A | مخاطبین، درخواست‌ها، رضایت پیامک | ✅ کامل | 100% |
| **2B** | **تایم‌لاین، بازدید، وظایف، اعلان‌ها** | **✅ کامل** | **100%** |
| 3 | Matching engine + Dashboard | ✅ کامل | 100% |
| 4 (roadmap) | پیامک و اشتراک عمومی | ⬜ شروع نشده | 0% |
| 4 (ما ساختیم) | Publishing به پورتال‌ها | ✅ کامل | 100% |
| 5–11 | صدا، رندر، انتشار، حسابداری، AI، ... | ⬜ شروع نشده | 0% |

---

## ۲. آنچه در این جلسه کامل شد

### فاز 2B — تایم‌لاین، بازدید، وظایف، اعلان

- **[`apps/crm/models.py`](../apps/crm/models.py)**
  - `Interaction` — تایم‌لاین تعاملات: FKهای صریح nullable به contact/listing/request
    (بدون GenericFK) + `CheckConstraint` حداقل یک هدف، ایندکس‌ها
  - `Visit` — بازدید فایل ↔ مخاطب با وضعیت و نتیجه
  - `Task` — وظیفه با assignee، موعد، اولویت، `reminder_sent_at` (گارد یک‌بارمصرف یادآوری)
  - `Notification` — اعلان درون‌برنامه‌ای (badge + list)
- **[`apps/crm/services.py`](../apps/crm/services.py)** — `add_interaction`, `get_timeline`,
  `schedule_visit` (همراه Interaction), `complete_visit`, `create_task`, `complete_task`, `notify`
- **[`apps/crm/tasks.py`](../apps/crm/tasks.py)** — `send_due_task_reminders` (Beat هر ۳۰ دقیقه، idempotent)
- **[`apps/crm/views.py`](../apps/crm/views.py)** + **[`apps/crm/urls.py`](../apps/crm/urls.py)** —
  timeline, visit create/complete (HTMX), tasks list/toggle (HTMX), my-day, notifications
- **Templates:** `crm/timeline.html`, `crm/tasks.html`, `crm/my_day.html`,
  `crm/notifications.html`, `crm/partials/visit_row.html`, `crm/partials/task_row.html`
- **[`templates/base.html`](../templates/base.html)** — badge اعلان + لینک «امروز من»
  (تگ جدید `unread_notifications_badge` در `core_tags.py`)
- **[`templates/listings/detail.html`](../templates/listings/detail.html)** — بخش بازدیدها + تایم‌لاین
- Migration: `crm/0004_interaction_notification_task_visit`
- **URL mount جابه‌جا شد:** `/crm/requests/` → `/crm/` (نام URLها ثابت ماند، قالب‌ها بی‌تأثیر)
- تنظیمات: `CELERY_BEAT_SCHEDULE` در base.py، `BASE_DIR` در testing_nogis.py
- **۲۶ تست** در `tests/test_2b_timeline_visit_tasks.py` (مجموعاً ۲۱۸ تست)

---

## ۳. تست‌ها (218 passing — بدون PostGIS)

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
| `tests/test_2b_timeline_visit_tasks.py` | **26** |
| **جمع** | **218** |

---

## ۴. آنچه نیمه‌کاره است

### ۴.۱ فازهای بعدی (اولویت‌بندی)
1. **4A (roadmap)** — زیرساخت پیامک (adapter واقعی SMS: Kavenegar و ...)
2. **4B (roadmap)** — ارسال خودکار تطبیق، فرم اشتراک عمومی
3. **5A** — صدا و ثبت هوشمند (MVP اصلی پروژه)

### ۴.۲ موارد نیمه‌کاره
- `test_tenant_isolation.py` — تست‌های pre-existing broken
- `test_health.py` — pre-existing broken
- **migration معلق accounts** (گروه‌های پیش‌فرض CustomUser) — از قبل وجود داشت، مربوط به 2B نیست
- ایمپورت xlsx نیاز به `openpyxl` دارد (در `pyproject.toml` نیست — در Docker نصب شود)
- Media در production نیاز به django-storages + MinIO
- **فرم سریع بازدید/وظیفه** فعلاً از آی‌دی عددی استفاده می‌کند (در فازهای بعدی combobox واقعی می‌شود)
- نقش منشی: فیلدهای شماره مالک در views جدید هنوز فیلتر نشده (در فاز 4A/9A با ماتریس نقش کامل انجام می‌شود)

---

## ۵. تله‌ها و نکته‌های محیطی

| موضوع | جزئیات |
|--------|---------|
| **Python** | 3.13.0 |
| **Django** | 5.2 LTS |
| **GDAL** | روی Windows نصب نیست |
| **Fernet key** | `_Rb6cmq4gjE2pZRi7BalzwZb49Amh9s0NGmxP0dbyW4=` |
| **normalize_fa** | در `apps/core/text.py` — همیشه از همینجا import کنید |
| **URL پیشوند CRM** | حالا `/crm/` است (قبلاً `/crm/requests/` بود) |
| **testing_nogis** | مستقل از base است؛ `BASE_DIR` را خودش تعریف می‌کند |
| **Celery Beat** | `send_due_task_reminders` هر ۳۰ دقیقه؛ `CELERY_TASK_ALWAYS_EAGER` در تست |
| **ImportJob** | `run_import_job_task.delay(job.pk)` — در Celery |
| **openpyxl** | `pip install openpyxl` برای تست xlsx در dev |
| **dev server** | `python manage.py runserver 8070 --settings=ara_amlak.settings.local_sqlite` |

---

## ۶. وضعیت گیت

- شاخه: `phase/2b-timeline-visit-tasks` (از `phase/1d-search-filter-import` ساخته شده)
- `[ ]` کامیت‌های این فاز هنوز پوش نشده‌اند
- پروژه گراف: `I-amlak` (تازه ایندکس شده، ۱۵۶۱ نود)

---

## ۷. قدم‌های بعدی به ترتیب

1. کامیت و پوش این شاخه + ساخت PR
2. فاز 4A (roadmap): interface `SMSProvider` + آداپتر کاوه‌نگار/ملی‌پیامک + Console/Fake
3. فاز 4B: ارسال خودکار تطبیق، ساعت مجاز، سقف روزانه، فرم عمومی OTP

---

## ۸. دستورهای اجرا و تست

```powershell
# تست no-GIS (218 تست)
python -m pytest --ds=ara_amlak.settings.testing_nogis tests/ `
  --ignore=tests/test_tenant_isolation.py `
  --ignore=tests/test_health.py -v

# lint
python -m ruff check .

# dev server (port 8070)
python manage.py runserver 8070 --settings=ara_amlak.settings.local_sqlite
# login: 09000000000 / admin1234
```

---

*این فایل را در ابتدای هر جلسه بخوان. قبل از شروع کد، `git status` و آخرین تست را اجرا کن.*
