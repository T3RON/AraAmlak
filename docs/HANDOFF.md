# HANDOFF — آرا املاک / Ara Amlak

**آخرین به‌روزرسانی:** پس از تکمیل فازهای 0C / 1A / 2A
**شاخه‌های جاری:** `phase/0c-roles-audit-invite` · `phase/1a-geo-models` · `phase/2a-contact-consent`
**آخرین کامیت:** `9f6e31f` — feat(crm): phase 2A

---

## ۱. فاز جاری و پیشرفت

| فاز | موضوع | وضعیت | درصد |
|-----|--------|--------|------|
| 0a | زیرساخت (Docker, CI, pre-commit) | ✅ کامل | 100% |
| 0B | دیزاین‌سیستم Apple-style | ⚠️ نسبی | 60% |
| **0C** | **هویت کاربر، نقش‌ها، AuditLog، دعوت عضو** | **✅ کامل** | **100%** |
| **1A** | **مدل داده فایل (City/Neighborhood/Feature)** | **✅ کامل** | **100%** |
| 1B | صفحات CRUD فایل | ✅ کامل | 100% |
| 1C | رسانه (آپلود عکس) | ⬜ شروع نشده | 0% |
| 1D | جستجو، فیلتر، نقشه، ایمپورت | ⬜ شروع نشده | 0% |
| **2A** | **مخاطبین، درخواست‌ها، رضایت پیامک** | **✅ کامل** | **100%** |
| 2B | تایم‌لاین، بازدید، وظایف | ⬜ شروع نشده | 0% |
| 3 | Matching engine + Dashboard | ✅ کامل | 100% |
| 4 (roadmap) | پیامک و اشتراک عمومی | ⬜ شروع نشده | 0% |
| 4 (ما ساختیم) | Publishing به پورتال‌ها | ✅ کامل | 100% |
| 5–11 | صدا، رندر، انتشار، حسابداری، AI، ... | ⬜ شروع نشده | 0% |

---

## ۲. آنچه در این جلسه کامل شد

### فاز 0C — نقش‌ها، AuditLog، دعوت عضو

- [`apps/accounts/permissions.py`](../apps/accounts/permissions.py)
  - `PERMISSION_MATRIX` — ماتریس دسترسی در یک فایل مرکزی
  - `has_permission()`, `RoleRequired` mixin, `role_required` decorator
- [`apps/core/models.py`](../apps/core/models.py) — `AuditLog` + `AuditLog.log()` factory
  - actions: login/logout/create/update/delete/view_phone/invite/publish/other
- [`apps/agencies/models.py`](../apps/agencies/models.py) — `Invitation` (single-use, token, expiry, `accept()`)
- [`apps/accounts/invite_views.py`](../apps/accounts/invite_views.py) — invite_create, invite_list, `InviteAcceptView` (OTP دو-مرحله‌ای)
- templates: `invite_create.html`, `invite_list.html`, `invite_accept.html`
- migrations: `core/0002_initial`, `agencies/0003_invitation`
- تست‌ها: **18 passing** در `tests/test_0c_roles_audit_invite.py`

### فاز 1A — مدل داده کامل فایل ملک

- `City` — شهر با استان و slug یکتا
- `Neighborhood` — محله با aliases برای جستجوی گفتاری و فازی
- `NeighborhoodAdjacency` — جدول همجواری (ویرایش‌پذیر بدون کد)
- `Feature` — امکانات M2M (آسانسور، پارکینگ، ...)
- `Listing` — اضافه‌شده: `neighborhood` FK، `location` (GIS/text)، `land_area`، `units_per_floor`، `balcony`، `features` M2M، CheckConstraint `floor ≤ total_floors`
- `ListingStatusHistory` — تاریخچه تغییر وضعیت append-only
- `ListingImage` — اضافه‌شده: `caption` field
- migration: `listings/0003`
- تست‌ها: **16 passing** در `tests/test_1a_geo_models.py`

### فاز 2A — مخاطبین، رضایت پیامک

- `Contact` — مخاطب tenant-scoped، phone رمزنگاری‌شده + phone_normalized برای index، `merge_into()`
- `ContactPhone` — چند شماره برای هر مخاطب
- `ConsentRecord` — رضایت دریافت پیامک append-only با `revoke()`
- `Request` — اضافه‌شده: `contact` FK، `expires_at` (auto 60d)، `PUBLIC_FORM` source، `EXPIRED` status
- migration: `crm/0003`
- تست‌ها: **16 passing** در `tests/test_2a_contact_consent.py`

---

## ۳. تست‌ها (135 passing — بدون PostGIS)

| فایل | تعداد |
|------|-------|
| `tests/test_otp.py` | 9 |
| `tests/test_listings_nogis.py` | 10 |
| `tests/test_crm_nogis.py` | 8 |
| `tests/test_matching_nogis.py` | 13 |
| `tests/test_publishing_nogis.py` | 12 |
| `tests/test_core_currency.py` | 16 |
| `tests/test_encrypted_field.py` | 4 |
| `tests/test_0c_roles_audit_invite.py` | **18** |
| `tests/test_1a_geo_models.py` | **16** |
| `tests/test_2a_contact_consent.py` | **16** |
| **جمع** | **135** |

> تست‌های GIS (`test_listings_isolation.py`, `test_crm_isolation.py`, `test_tenant_isolation.py`) فقط در Docker/CI اجرا می‌شوند.

---

## ۴. آنچه نیمه‌کاره است

### ۴.۱ فازهای بعدی (اولویت‌بندی)
1. **1C** — آپلود چندتایی عکس (MinIO/S3، Celery thumbnail)
2. **1D** — جستجو، فیلتر pg_trgm، ایمپورت Excel
3. **2B** — تایم‌لاین، بازدید، وظایف
4. **4A (roadmap)** — زیرساخت پیامک (adapter واقعی SMS)
5. **4B (roadmap)** — ارسال خودکار تطبیق، فرم اشتراک عمومی

### ۴.۲ موارد نیمه‌کاره
- Invitation: URL در `ara_amlak/urls.py` باید confirm شود (از `auth/` prefix استفاده می‌کند)
- `test_tenant_isolation.py` — تست‌های pre-existing broken (مربوط به factory_boy factories)
- `test_health.py` — یک تست `home.html` broken (pre-existing)

---

## ۵. تله‌ها و نکته‌های محیطی

| موضوع | جزئیات |
|--------|---------|
| **Python** | 3.13.0 |
| **Django** | 5.2 LTS |
| **GDAL** | روی Windows نصب نیست |
| **Fernet key** | `testing_nogis.py` = `_Rb6cmq4gjE2pZRi7BalzwZb49Amh9s0NGmxP0dbyW4=` |
| **phone_normalized** | باید توسط caller قبل از save ست شود (phone رمزنگاری‌شده است) |
| **ConsentRecord** | append-only — هرگز update نکنید؛ فقط `revoke()` |
| **AuditLog** | append-only — هرگز update/delete نکنید |

---

## ۶. دستورهای اجرا و تست

```powershell
# تست no-GIS (135 تست)
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
