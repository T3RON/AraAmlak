# HANDOFF — آرا املاک / Ara Amlak

**آخرین به‌روزرسانی:** پس از تکمیل فاز 1D — جستجو، فیلتر، normalize_fa، ImportJob
**شاخه جاری:** `phase/1d-search-filter-import`
**آخرین کامیت:** `e1ce7c2` — feat(listings,core): complete phase 1D

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
| **1D** | **جستجو، فیلتر، normalize_fa، ImportJob** | **✅ کامل** | **100%** |
| 2A | مخاطبین، درخواست‌ها، رضایت پیامک | ✅ کامل | 100% |
| 2B | تایم‌لاین، بازدید، وظایف | ⬜ شروع نشده | 0% |
| 3 | Matching engine + Dashboard | ✅ کامل | 100% |
| 4 (roadmap) | پیامک و اشتراک عمومی | ⬜ شروع نشده | 0% |
| 4 (ما ساختیم) | Publishing به پورتال‌ها | ✅ کامل | 100% |
| 5–11 | صدا، رندر، انتشار، حسابداری، AI، ... | ⬜ شروع نشده | 0% |

---

## ۲. آنچه در این جلسه کامل شد

### فاز 1C — رسانه (Media)
- مدل `Media` + MIME detection + EXIF strip + thumbnail/WebP Celery + signed URL
- ۱۹ تست

### فاز 1D — جستجو، فیلتر، normalize_fa، ImportJob

- **[`apps/core/text.py`](../apps/core/text.py)**
  - `normalize_fa()` — کاف/یاء عربی، ارقام شرقی، ZWNJ، فضاهای اضافه
  - `normalize_phone_ir()` — نرمال‌سازی شماره موبایل ایران
- **[`apps/listings/search_service.py`](../apps/listings/search_service.py)**
  - `build_listing_queryset(params)` — فیلتر کامل با Q lookup (سازگار با SQLite)
- **[`apps/listings/import_service.py`](../apps/listings/import_service.py)**
  - `parse_import_file()` — xlsx/csv با auto-detect
  - `_coerce_row()` — تبدیل نوع با اعتبارسنجی
  - `check_duplicate()` — تشخیص تکراری ±10% area
  - `run_import_job()` — pipeline کامل ایمپورت
- **[`apps/listings/models.py`](../apps/listings/models.py)** — `ImportJob` مدل (AgencyOwned)
- **[`apps/listings/import_views.py`](../apps/listings/import_views.py)** — upload + detail + HTMX progress
- **[`apps/listings/tasks.py`](../apps/listings/tasks.py)** — `run_import_job_task` (Celery)
- **Templates:**
  - `templates/listings/list.html` — فیلتر کامل + جستجو HTMX
  - `templates/listings/partials/listing_cards.html` — کارت‌ها جدا شد
  - `templates/listings/import.html` + `import_detail.html`
  - `templates/listings/partials/import_status.html` — polling 2s
- Migration: `listings/0005_import_job`
- **38 تست** در `tests/test_1d_search_import.py`

---

## ۳. تست‌ها (192 passing — بدون PostGIS)

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
| `tests/test_1d_search_import.py` | **38** |
| **جمع** | **192** |

---

## ۴. آنچه نیمه‌کاره است

### ۴.۱ فازهای بعدی (اولویت‌بندی)
1. **2B** — تایم‌لاین، بازدید، وظایف، Celery Beat reminders
2. **4A (roadmap)** — زیرساخت پیامک (adapter واقعی SMS: Kavenegar و ...)
3. **4B (roadmap)** — ارسال خودکار تطبیق، فرم اشتراک عمومی
4. **5A** — صدا و ثبت هوشمند (MVP اصلی پروژه)

### ۴.۲ موارد نیمه‌کاره
- `test_tenant_isolation.py` — تست‌های pre-existing broken
- `test_health.py` — pre-existing broken
- ایمپورت xlsx نیاز به `openpyxl` دارد (در `pyproject.toml` نیست — در Docker نصب شود)
- Media در production نیاز به django-storages + MinIO

---

## ۵. تله‌ها و نکته‌های محیطی

| موضوع | جزئیات |
|--------|---------|
| **Python** | 3.13.0 |
| **Django** | 5.2 LTS |
| **GDAL** | روی Windows نصب نیست |
| **Fernet key** | `_Rb6cmq4gjE2pZRi7BalzwZb49Amh9s0NGmxP0dbyW4=` |
| **normalize_fa** | در `apps/core/text.py` — همیشه از همینجا import کنید |
| **ImportJob** | `run_import_job_task.delay(job.pk)` — در Celery؛ CELERY_TASK_ALWAYS_EAGER در test |
| **openpyxl** | `pip install openpyxl` برای تست xlsx در dev |
| **dev server** | `python manage.py runserver 8070 --settings=ara_amlak.settings.local_sqlite` |

---

## ۶. دستورهای اجرا و تست

```powershell
# تست no-GIS (192 تست)
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
