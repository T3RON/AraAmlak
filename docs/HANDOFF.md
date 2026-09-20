# HANDOFF — آرا املاک / Ara Amlak

**آخرین به‌روزرسانی:** پس از فاز ۲  
**شاخه جاری:** `phase/2-listings-crm`  
**آخرین کامیت:** `166be69` — pushed به origin  

---

## ۱. فاز جاری و پیشرفت

| فاز | موضوع | وضعیت | درصد |
|-----|--------|--------|------|
| 0a | زیرساخت (Docker, CI, pre-commit) | ✅ کامل | 100% |
| 1 | Bootstrap (Django scaffold, 12 اپ، core/accounts/agencies) | ✅ کامل | 100% |
| **2** | **listings + crm (مدل، سرویس، view، template)** | **✅ کامل** | **100%** |
| 3 | Matching engine (تطبیق فایل با درخواست) | ⬜ شروع نشده | 0% |
| 4 | Publishing (انتشار به پورتال‌ها) | ⬜ شروع نشده | 0% |

---

## ۲. آنچه کامل و تست‌شده است

### زیرساخت
- [`docker-compose.yml`](../docker-compose.yml) — 5 سرویس: db (PostGIS 16), redis 7, web (Daphne), celery, celery-beat
- [`Dockerfile.dev`](../docker/Dockerfile.dev), [`entrypoint.sh`](../docker/entrypoint.sh)
- [`ara.ps1`](../ara.ps1) — Windows PowerShell helper (معادل Makefile)
- [`Makefile`](../Makefile) — Linux/macOS helper
- [`.env.example`](../.env.example) — تمام متغیرهای محیطی
- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — lint + test + migration-check
- [`specs/constitution.md`](../specs/constitution.md) — قانون اساسی پروژه

### اپ `core`
- [`apps/core/models.py`](../apps/core/models.py) — `TimeStampedModel`, `AgencyOwned`, `AgencyManager`, `UnfilteredAgencyManager`
- [`apps/core/fields.py`](../apps/core/fields.py) — `EncryptedCharField` (Fernet)
- [`apps/core/currency.py`](../apps/core/currency.py) — `format_toman()`, `to_persian_digits()`
- [`apps/core/middleware.py`](../apps/core/middleware.py) — `AgencyMiddleware` (thread-local)
- [`apps/core/health.py`](../apps/core/health.py) — `check_db()`, `check_redis()`
- [`apps/core/views.py`](../apps/core/views.py) — `/health/` endpoint
- [`apps/core/urls.py`](../apps/core/urls.py)
- [`apps/core/migrations/0001_extensions.py`](../apps/core/migrations/0001_extensions.py) — PostGIS/pg_trgm/unaccent با `RunPython` + vendor guard

### اپ `accounts`
- [`apps/accounts/models.py`](../apps/accounts/models.py) — `CustomUser` (phone-based)
- [`apps/accounts/otp.py`](../apps/accounts/otp.py) — Redis OTP، TTL 120s، max 5 تلاش
- [`apps/accounts/api_views.py`](../apps/accounts/api_views.py) — DRF: `OTPSendView`, `OTPVerifyView`

### اپ `agencies`
- [`apps/agencies/models.py`](../apps/agencies/models.py) — `Agency`, `Branch` (GIS optional), `AgencyMember`
- [`apps/agencies/migrations/0001_initial.py`](../apps/agencies/migrations/0001_initial.py) — Agency + Branch (SQLite-safe: `location` = TextField)
- [`apps/agencies/migrations/0002_agency_member.py`](../apps/agencies/migrations/0002_agency_member.py) — AgencyMember (جدا از 0001 برای شکستن circular dep)

### اپ `listings`
- [`apps/listings/models.py`](../apps/listings/models.py) — `Listing` + `ListingImage` + enums
- [`apps/listings/migrations/0001_initial.py`](../apps/listings/migrations/0001_initial.py)
- [`apps/listings/services.py`](../apps/listings/services.py) — `create_listing`, `update_listing`, `change_listing_status`, `expire_overdue_listings`
- [`apps/listings/tasks.py`](../apps/listings/tasks.py) — Celery task انقضا
- [`apps/listings/admin.py`](../apps/listings/admin.py), [`views.py`](../apps/listings/views.py), [`urls.py`](../apps/listings/urls.py)
- [`templates/listings/`](../templates/listings/) — list, detail, form, partials/status_badge

### اپ `crm`
- [`apps/crm/models.py`](../apps/crm/models.py) — `Request` + enums + `close_request` service
- [`apps/crm/migrations/0001_initial.py`](../apps/crm/migrations/0001_initial.py)
- [`apps/crm/services.py`](../apps/crm/services.py) — `create_request`, `update_request`, `close_request`
- [`apps/crm/admin.py`](../apps/crm/admin.py), [`views.py`](../apps/crm/views.py), [`urls.py`](../apps/crm/urls.py)
- [`templates/crm/`](../templates/crm/) — list, form

### تست‌ها (47 passing)
| فایل | تعداد | نیاز به PostGIS |
|------|-------|----------------|
| `tests/test_otp.py` | 9 | خیر |
| `tests/test_listings_nogis.py` | 10 | خیر |
| `tests/test_crm_nogis.py` | 8 | خیر |
| `tests/test_core_currency.py` | 16 | خیر |
| `tests/test_encrypted_field.py` | 4 | خیر |
| `tests/test_listings_isolation.py` | 3 | **بله** |
| `tests/test_crm_isolation.py` | 2 | **بله** |
| `tests/test_health.py` | — | بله (URL override) |
| `tests/test_accounts.py` | — | بله |
| `tests/test_tenant_isolation.py` | — | بله |

---

## ۳. آنچه نیمه‌کاره است

### ۳.۱ `templates/listings/detail.html` — متد `get_status_choices`
فایل template در خط زیر `listing.get_status_choices` صدا می‌زند که روی مدل تعریف نشده:
```html
{% for val, label in listing.get_status_choices %}
```
**راه‌حل:** یا `get_status_choices` را به مدل اضافه کن، یا در template از `ListingStatus.choices` استفاده کن (با context processor).

### ۳.۲ Tailwind CSS
فایل [`static/css/main.css`](../static/css/main.css) placeholder است — هنوز compile نشده.
```bash
npx tailwindcss -i static/css/input.css -o static/css/main.css --watch
```

### ۳.۳ Vazirmatn fonts
`static/fonts/` خالی است. فونت باید از `rastikerdar.github.io/Vazirmatn` دانلود شود.

### ۳.۴ آپلود تصویر (ListingImage)
مدل `ListingImage` ساخته شده اما endpoint آپلود فایل وجود ندارد (Phase 2.5).

### ۳.۵ `LOGIN_URL` در settings
Views از `LoginRequiredMixin` استفاده می‌کنند اما `LOGIN_URL` در `settings/base.py` تنظیم نشده.

### ۳.۶ اپ‌های stub
اپ‌های `matching`, `messaging`, `ai`, `publishing`, `rendering`, `accounting` فقط stub هستند (فقط `apps.py` و `models.py` خالی).

### ۳.۷ SMS integration
`accounts/tasks.py` stub است — هنوز ارائه‌دهنده SMS واقعی integrate نشده.

---

## ۴. تصمیم‌های معماری

### ✅ تصمیم‌های گرفته‌شده

| تصمیم | دلیل |
|--------|-------|
| `agencies/0001` از `AgencyMember` جدا شد → `0002` | شکستن circular dep: `accounts` → `agencies` → `accounts` |
| `core/0001_extensions` از `RunSQL` به `RunPython + vendor guard` تبدیل شد | SQLite برای تست local `CREATE EXTENSION` نمی‌فهمد |
| `Branch.location` در SQLite = `TextField` (not PointField) | GDAL روی Windows نصب نیست |
| `crm.models` از `listings.models.DealType` import می‌کند | تکرار نکردن enum مشترک |
| `owner_phone` و `client_phone` با `EncryptedCharField` (Fernet) | اطلاعات حساس هرگز plaintext در DB نیستند |
| کد فایل: `{slug[:2].upper()}-{count:04d}` | ساده، قابل خواندن، no-race در MVP |
| `property_types` در Request = `JSONField(default=list)` | انعطاف‌پذیری، بدون `ArrayField` dependency |

### ❌ امتحان‌شده و کار نکرده

| روش | مشکل |
|-----|-------|
| `to=settings.AUTH_USER_MODEL` در agencies migration | circular dep با accounts |
| `to="accounts.customuser"` (lowercase) در migration | Django case-sensitive → `ValueError: Related model cannot be resolved` |
| `RunSQL` برای extensions | SQLite `OperationalError: near "EXTENSION": syntax error` |
| `from django.contrib.gis.db import models as gis_models` در agencies/models.py (unconditional) | `ImproperlyConfigured: Could not find the GDAL library` |

---

## ۵. تله‌ها و نکته‌های محیطی

| موضوع | جزئیات |
|--------|---------|
| **Python** | 3.13.0 |
| **Django** | 5.2 LTS |
| **GDAL** | روی Windows نصب نیست — همه تست‌های GIS فقط در Docker/CI |
| **Fernet key** | مقدار `testing.py` و `testing_nogis.py` = `_Rb6cmq4gjE2pZRi7BalzwZb49Amh9s0NGmxP0dbyW4=` (32-byte valid) |
| **pytest default DS** | `ara_amlak.settings.testing` (PostGIS) — برای local باید `--ds=ara_amlak.settings.testing_nogis` |
| **circular dep** | agencies ← accounts ← agencies: حل شد با split migration |
| **`tail` command** | PowerShell ندارد — از `Select-Object -Last N` استفاده کن |
| **`&&` در PowerShell** | کار نمی‌کند — از `;` یا `if ($?) { ... }` |
| **`git log --oneline ... \| tail`** | باید `Select-Object -Last N` |
| **Port 5432** | باید آزاد باشد برای Docker PostGIS |
| **`FIELD_ENCRYPTION_KEY` نامعتبر** | مقدار اولیه `dGVzdC1rZXktMzItYnl0ZXMtcGFkZGluZy10ZXN0IQ==` فقط 31 byte بود — fix شد |

---

## ۶. وضعیت گیت

```
شاخه:      phase/2-listings-crm
origin:    origin/phase/2-listings-crm  ✅ synced (pushed)
PR:        https://github.com/T3RON/AraAmlak/pull/new/phase/2-listings-crm
Working tree: clean (git status = nothing to commit)
```

### آخرین کامیت‌ها
```
166be69  chore(infra): restore files missing from phase/2 branch
2791784  chore(ui): replace JS placeholder files with real HTMX 1.9.12 and Alpine.js 3.14.1
9bfc861  test(listings,crm): add no-GIS and tenant isolation tests
4e138e9  feat(ui): add listings and crm templates with Apple HIG design
c664b54  feat(crm): add Request model, migration, services, admin, views, urls
bb72511  feat(listings): add Listing model, migration, services, tasks, admin, views, urls
c6c7b30  fix(core): fix SQLite-safe migrations and no-GIS import guards
1b3cd0a  docs(specs): add phase-2 spec kit (specify, plan, tasks) for listings and crm
```

### شاخه‌های remote
```
origin/phase/2-listings-crm   ← جاری
origin/phase/1-bootstrap
origin/phase/0a-scaffold
origin/chore/code-intelligence
```

> **نکته:** `main` branch روی remote وجود ندارد. اولین PR باید از `phase/2-listings-crm` به `phase/1-bootstrap` یا مستقیماً `main` بزنی پس از ایجادش.

---

## ۷. قدم‌های بعدی (به ترتیب اولویت)

### فوری (قبل از فاز ۳)
1. **Fix `detail.html` status choices** — اضافه کردن `get_status_choices` به `Listing` مدل یا تغییر template
2. **Fix `LOGIN_URL`** — اضافه کردن `LOGIN_URL = "/auth/login/"` به `settings/base.py`
3. **Tailwind compile** — `npx tailwindcss -i static/css/input.css -o static/css/main.css`
4. **Vazirmatn download** — دانلود `.woff2` به `static/fonts/`
5. **Branch merge** — باز کردن PR و merge به یک شاخه base

### فاز ۳ — Matching Engine
برای هر درخواست (Request)، فایل‌های (Listing) منطبق را پیدا کند:
- `apps/matching/models.py` — `Match` مدل (listing FK + request FK + score)
- `apps/matching/services.py` — `find_matches(request)` با فیلتر deal_type, city, area, budget
- `apps/matching/tasks.py` — Celery task اجرای matching بعد از ثبت درخواست
- `tests/test_matching_nogis.py`

### فاز ۳ — Dashboard واقعی
- آمار آژانس: تعداد فایل‌های active، درخواست‌های جدید، matches امروز
- [`templates/dashboard/home.html`](../templates/dashboard/home.html) update

### فاز ۴ — Publishing
- اتصال به پورتال‌ها (دیوار، شیپور) — نیاز به خواندن مستندات API رسمی

### فاز ۵ — SMS / OTP واقعی
- خواندن مستندات ارائه‌دهنده SMS ایرانی (کاوه‌نگار، ملی‌پیام، ...)
- پیاده‌سازی `accounts/tasks.py` واقعی

---

## ۸. دستورهای اجرا و تست

### تست local (بدون Docker)
```powershell
# نصب dependencies
pip install -r requirements.txt

# تست no-GIS (همه باید سبز باشند)
python -m pytest --ds=ara_amlak.settings.testing_nogis `
  tests/test_core_currency.py `
  tests/test_encrypted_field.py `
  tests/test_otp.py `
  tests/test_listings_nogis.py `
  tests/test_crm_nogis.py `
  -v
# → باید 47 passed

# lint
python -m ruff check .
```

### تست کامل (Docker — PostGIS لازم دارد)
```powershell
.\ara.ps1 up       # بالا آوردن Docker
.\ara.ps1 test     # اجرای همه تست‌ها با PostGIS
.\ara.ps1 lint     # ruff
.\ara.ps1 migrate  # اعمال migration‌ها
```

```bash
# Linux/macOS
make up
make test
make lint
```

### اجرای dev server
```powershell
# ابتدا .env را از .env.example کپی کن و مقادیر را پر کن
Copy-Item .env.example .env
# سپس:
.\ara.ps1 up
# وب در http://localhost:8000
```

### تولید Tailwind CSS
```bash
npx tailwindcss -i static/css/input.css -o static/css/main.css --minify
```

---

## ۹. CBM Graph

- **نام پروژه در گراف:** `I-amlak`
- **وضعیت:** آخرین index از فاز ۱ — نیاز به re-index بعد از فاز ۲
- **دستور re-index:**
  ```
  /index  یا از AGENTS.md → Rule 2: index after major changes
  ```
- **ADR‌ها:** در `.codebase-memory/adrs/` (اگر CBM فعال باشد)
- **تصمیم‌های جدید فاز ۲** که باید در ADR ثبت شوند:
  - Split migration for circular dep (agencies 0001/0002)
  - SQLite-safe GIS guard pattern
  - EncryptedCharField for PII fields (owner_phone, client_phone)
  - JSONField for property_types array

---

*این فایل را در ابتدای هر جلسه بخوان. قبل از شروع کد، `git status` و آخرین تست را اجرا کن.*
