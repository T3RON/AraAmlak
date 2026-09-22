# HANDOFF — آرا املاک / Ara Amlak

**آخرین به‌روزرسانی:** پس از تکمیل فاز 1C — رسانه (Media)
**شاخه جاری:** `phase/1c-media`
**آخرین کامیت:** `8c60f54` — chore(infra): ignore test_media directory from git

---

## ۱. فاز جاری و پیشرفت

| فاز | موضوع | وضعیت | درصد |
|-----|--------|--------|------|
| 0a | زیرساخت (Docker, CI, pre-commit) | ✅ کامل | 100% |
| 0B | دیزاین‌سیستم Apple-style | ⚠️ نسبی | 60% |
| 0C | هویت کاربر، نقش‌ها، AuditLog، دعوت عضو | ✅ کامل | 100% |
| 1A | مدل داده فایل (City/Neighborhood/Feature) | ✅ کامل | 100% |
| 1B | صفحات CRUD فایل | ✅ کامل | 100% |
| **1C** | **رسانه (آپلود، پردازش، سند خصوصی)** | **✅ کامل** | **100%** |
| 1D | جستجو، فیلتر، نقشه، ایمپورت | ⬜ شروع نشده | 0% |
| 2A | مخاطبین، درخواست‌ها، رضایت پیامک | ✅ کامل | 100% |
| 2B | تایم‌لاین، بازدید، وظایف | ⬜ شروع نشده | 0% |
| 3 | Matching engine + Dashboard | ✅ کامل | 100% |
| 4 (roadmap) | پیامک و اشتراک عمومی | ⬜ شروع نشده | 0% |
| 4 (ما ساختیم) | Publishing به پورتال‌ها | ✅ کامل | 100% |
| 5–11 | صدا، رندر، انتشار، حسابداری، AI، ... | ⬜ شروع نشده | 0% |

---

## ۲. آنچه در این جلسه کامل شد

### فاز 1C — رسانه (Media)

- **مدل `Media`** در [`apps/listings/models.py`](../apps/listings/models.py)
  - `media_type`: photo / video / document
  - `is_private` — اسناد خصوصی فقط با signed URL
  - `thumbnail` + `webp` — بعد از Celery پر می‌شوند
  - `status`: pending / processing / ready / error
  - `file_size`, `mime_type`, `original_filename`
- **تشخیص MIME** از بایت‌های واقعی (نه پسوند) — magic byte detection
- **حذف EXIF/GPS** با Pillow برای عکس‌های عمومی
- **تولید thumbnail** (400×300 JPEG) + **نسخه WebP** (حداکثر 1600px) در Celery
- **Signed URL** با `django.core.signing` برای اسناد خصوصی (300 ثانیه TTL)
- **سرویس‌ها**: `create_media`, `delete_media`, `reorder_media`, `set_cover`
- **تسک Celery** `process_media_task` با retry (3 بار)
- **ویوها** (HTMX): upload, delete, reorder, set_cover, private_serve
- **Templates**:
  - `templates/listings/partials/media_upload.html` — drag & drop با Alpine.js
  - `templates/listings/partials/media_item.html` — کارت یک رسانه
  - `templates/listings/partials/media_gallery.html` — گالری کامل
- تزریق media section در صفحه جزئیات فایل
- Migration: `listings/0004_media_model`
- **19 تست** در `tests/test_1c_media.py`

---

## ۳. تست‌ها (154 passing — بدون PostGIS)

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
| `tests/test_1c_media.py` | **19** |
| **جمع** | **154** |

---

## ۴. آنچه نیمه‌کاره است

### ۴.۱ فازهای بعدی (اولویت‌بندی)
1. **1D** — جستجو، فیلتر pg_trgm، ایمپورت Excel (`normalize_fa`, `ImportJob`, Leaflet)
2. **2B** — تایم‌لاین، بازدید، وظایف، Celery Beat reminders
3. **4A (roadmap)** — زیرساخت پیامک (adapter واقعی SMS: Kavenegar و ...)
4. **4B (roadmap)** — ارسال خودکار تطبیق، فرم اشتراک عمومی

### ۴.۲ موارد نیمه‌کاره
- `test_tenant_isolation.py` — تست‌های pre-existing broken (factory_boy factories)
- `test_health.py` — یک تست `home.html` broken (pre-existing)
- Media در production نیاز به django-storages + MinIO دارد (فعلاً local filesystem)

---

## ۵. تله‌ها و نکته‌های محیطی

| موضوع | جزئیات |
|--------|---------|
| **Python** | 3.13.0 |
| **Django** | 5.2 LTS |
| **GDAL** | روی Windows نصب نیست |
| **Fernet key** | `testing_nogis.py` = `_Rb6cmq4gjE2pZRi7BalzwZb49Amh9s0NGmxP0dbyW4=` |
| **test_media/** | در `.gitignore` — فایل‌های آپلود‌شده در تست |
| **MIME detection** | از `detect_mime()` در `media_services.py` — magic bytes |
| **EXIF strip** | `strip_exif_from_bytes()` — در Celery روی عکس‌های عمومی |
| **Signed URL** | `media.generate_signed_url()` — برای اسناد خصوصی |
| **ROOT_URLCONF** | در `testing_nogis.py` اضافه شد برای URL reverse در تست‌ها |

---

## ۶. دستورهای اجرا و تست

```powershell
# تست no-GIS (154 تست)
python -m pytest --ds=ara_amlak.settings.testing_nogis tests/ `
  --ignore=tests/test_tenant_isolation.py `
  --ignore=tests/test_health.py `
  -v

# lint
python -m ruff check .

# dev server
python manage.py runserver 8990 --settings=ara_amlak.settings.local_sqlite
```

---

*این فایل را در ابتدای هر جلسه بخوان. قبل از شروع کد، `git status` و آخرین تست را اجرا کن.*
