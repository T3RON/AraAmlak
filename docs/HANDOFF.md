# HANDOFF — آرا املاک / Ara Amlak

**آخرین به‌روزرسانی:** پس از فاز ۳
**شاخه جاری:** `phase/3-matching-dashboard`
**آخرین کامیت:** `5cc174c` — tests(matching)

---

## ۱. فاز جاری و پیشرفت

| فاز | موضوع | وضعیت | درصد |
|-----|--------|--------|------|
| 0a | زیرساخت (Docker, CI, pre-commit) | ✅ کامل | 100% |
| 1 | Bootstrap (Django scaffold, 12 اپ، core/accounts/agencies) | ✅ کامل | 100% |
| 2 | listings + crm (مدل، سرویس، view، template) | ✅ کامل | 100% |
| **3** | **Matching engine + Dashboard واقعی** | **✅ کامل** | **100%** |
| 4 | Publishing (انتشار به پورتال‌ها) | ⬜ شروع نشده | 0% |
| 5 | SMS / OTP واقعی | ⬜ شروع نشده | 0% |

---

## ۲. آنچه کامل و تست‌شده است

### زیرساخت (فاز 0a / 1 / 2 — ثابت، تغییر نشده)
- Docker Compose، CI، pre-commit، Makefile، ara.ps1
- core/accounts/agencies/listings/crm — کامل‌شده در فازهای قبل

### اپ `matching` — جدید در فاز ۳
- [`apps/matching/models.py`](../apps/matching/models.py) — `Match` (agency FK, request FK, listing FK, score)
- [`apps/matching/services.py`](../apps/matching/services.py) — `find_matches(request)` با امتیازبندی ۵ معیاری
- [`apps/matching/tasks.py`](../apps/matching/tasks.py) — `run_matching_for_request` Celery task
- [`apps/matching/signals.py`](../apps/matching/signals.py) — post_save Request → task dispatch
- [`apps/matching/apps.py`](../apps/matching/apps.py) — `ready()` hook
- [`apps/matching/admin.py`](../apps/matching/admin.py)
- [`apps/matching/views.py`](../apps/matching/views.py) — `RequestMatchListView`
- [`apps/matching/urls.py`](../apps/matching/urls.py) — `/matching/requests/<pk>/matches/`
- [`apps/matching/migrations/0001_initial.py`](../apps/matching/migrations/0001_initial.py)
- [`templates/matching/match_list.html`](../templates/matching/match_list.html) — کارت‌های match با badge امتیاز

### امتیازبندی matching
| معیار | امتیاز |
|-------|--------|
| city یکسان | +۳۰ |
| property_type در property_types | +۲۵ |
| area در بازه | +۲۰ |
| قیمت در بودجه | +۱۵ |
| اتاق در بازه | +۱۰ |
| **حداکثر** | **۱۰۰** |

### داشبورد — بهبود یافته
- [`apps/dashboard/views.py`](../apps/dashboard/views.py) — ۵ کارت آماری
  - فایل‌های active، کل فایل‌ها، درخواست‌های جدید، کل درخواست‌ها، **تطبیق‌های امروز**
- [`templates/dashboard/home.html`](../templates/dashboard/home.html) — آپدیت شده

### تست‌ها (60 passing)
| فایل | تعداد | نیاز به PostGIS |
|------|-------|----------------|
| `tests/test_otp.py` | 9 | خیر |
| `tests/test_listings_nogis.py` | 10 | خیر |
| `tests/test_crm_nogis.py` | 8 | خیر |
| `tests/test_matching_nogis.py` | **13** | خیر |
| `tests/test_core_currency.py` | 16 | خیر |
| `tests/test_encrypted_field.py` | 4 | خیر |
| `tests/test_listings_isolation.py` | 3 | **بله** |
| `tests/test_crm_isolation.py` | 2 | **بله** |

---

## ۳. آنچه نیمه‌کاره است

### ۳.۱ آپلود تصویر (ListingImage)
مدل `ListingImage` ساخته شده اما endpoint آپلود فایل وجود ندارد (Phase 2.5 / بعداً).

### ۳.۲ Tailwind CSS
فایل `static/css/main.css` دارای CSS متغیرها و طراحی کامل است؛ اما از Tailwind compile نشده.
برای استفاده از class‌های Tailwind:
```bash
npx tailwindcss -i static/css/input.css -o static/css/main.css --watch
```

### ۳.۳ SMS integration
`accounts/tasks.py` stub است — ارائه‌دهنده SMS ایرانی integrate نشده (فاز ۵).

### ۳.۴ اپ‌های stub
اپ‌های `messaging`, `ai`, `publishing`, `rendering`, `accounting` فقط stub هستند.

### ۳.۵ Celery در dev local
در local_sqlite، `CELERY_TASK_ALWAYS_EAGER=False` — یعنی signal dispatch وجود دارد اما worker نمی‌دود.
برای دیدن matching در عمل: یا Docker Compose را بالا بیار (`.\ara.ps1 up`) یا `CELERY_TASK_ALWAYS_EAGER=True` در local_sqlite تنظیم کن.

---

## ۴. تصمیم‌های معماری

### ✅ تصمیم‌های گرفته‌شده (فاز ۳)

| تصمیم | دلیل |
|--------|-------|
| `Match.agency` denormalized | فیلتر tenant-scoped بدون JOIN |
| Signal dispatch (نه inline) | اجرای matching فقط در Celery — view نازک |
| `find_matches` upsert pattern | `bulk_create` + `bulk_update` بدون race condition در MVP |
| Hard filters: agency + deal_type + active status | حذف کامل نامنطبق‌ها قبل از scoring |
| Soft filters: score accumulation | هر معیار جداگانه — partial match امتیاز می‌گیرد |
| Score > 0 فقط persist می‌شود | جلوگیری از انباشته شدن سطر‌های بی‌ارزش |

### ✅ تصمیم‌های گرفته‌شده (فازهای قبل — بدون تغییر)
→ در نسخه قبلی HANDOFF مستند شده

### ❌ امتحان‌شده و کار نکرده (فازهای قبل)
→ در نسخه قبلی HANDOFF مستند شده

---

## ۵. تله‌ها و نکته‌های محیطی

| موضوع | جزئیات |
|--------|---------|
| **Python** | 3.13.0 |
| **Django** | 5.2 LTS |
| **GDAL** | روی Windows نصب نیست — همه تست‌های GIS فقط در Docker/CI |
| **Fernet key** | `testing_nogis.py` = `_Rb6cmq4gjE2pZRi7BalzwZb49Amh9s0NGmxP0dbyW4=` (32-byte valid) |
| **pytest default DS** | `ara_amlak.settings.testing` (PostGIS) — برای local باید `--ds=ara_amlak.settings.testing_nogis` |
| **Signal در dev** | `run_matching_for_request.delay()` در local بدون worker run نمی‌شود |
| **`&&` در PowerShell** | کار نمی‌کند — از `;` یا `if ($?) { ... }` |

---

## ۶. وضعیت گیت

```
شاخه:      phase/3-matching-dashboard
origin:    pending push
Working tree: clean
```

### کامیت‌های فاز ۳
```
5cc174c  test(matching): add 13 no-GIS tests for scoring, filters, isolation
aa3d632  feat(dashboard): add matches_today stat card and agency-scoped counts
b9afc11  feat(matching): add match list view, urls, template, crm list link
59369a5  feat(matching): add matching service, Celery task, post_save signal
3b76fb2  feat(matching): add Match model, migration, admin
5d64a79  fix(accounts): add LOGIN_URL, LOGIN_REDIRECT_URL to base settings
```

### شاخه‌های remote
```
origin/phase/3-matching-dashboard  ← جاری (پس از push)
origin/phase/2-listings-crm
origin/phase/1-bootstrap
origin/phase/0a-scaffold
```

---

## ۷. قدم‌های بعدی (به ترتیب اولویت)

### فاز ۴ — Publishing
- اتصال به پورتال‌ها (دیوار، شیپور)
- نیاز به خواندن مستندات API رسمی قبل از کدنویسی
- `apps/publishing/models.py` — `PortalConfig`, `PublishJob`

### فاز ۵ — SMS / OTP واقعی
- خواندن مستندات ارائه‌دهنده SMS ایرانی
- پیاده‌سازی `accounts/tasks.py` واقعی

### بهبودهای کوتاه‌مدت
- آپلود تصویر برای `ListingImage`
- `property_types` JSONField widget در CRM form → MultipleChoice

---

## ۸. دستورهای اجرا و تست

### تست local (بدون Docker)
```powershell
# تست no-GIS (همه باید سبز باشند — 60 passed)
python -m pytest --ds=ara_amlak.settings.testing_nogis `
  tests/test_core_currency.py `
  tests/test_encrypted_field.py `
  tests/test_otp.py `
  tests/test_listings_nogis.py `
  tests/test_crm_nogis.py `
  tests/test_matching_nogis.py `
  -v

# lint
python -m ruff check .
```

### اجرای dev server
```powershell
python manage.py runserver 8990 --settings=ara_amlak.settings.local_sqlite
# سپس در مرورگر: http://127.0.0.1:8990
# لاگین: 09000000000 (بررسی OTP در terminal)
# داشبورد: /dashboard/
# درخواست‌ها + تطبیق: /crm/requests/ → کلیک روی «تطبیق‌ها»
```

### تست کامل (Docker — PostGIS لازم دارد)
```powershell
.\ara.ps1 up
.\ara.ps1 test
.\ara.ps1 lint
```

---

*این فایل را در ابتدای هر جلسه بخوان. قبل از شروع کد، `git status` و آخرین تست را اجرا کن.*
