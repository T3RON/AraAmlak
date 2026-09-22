# HANDOFF — آرا املاک / Ara Amlak

**آخرین به‌روزرسانی:** پس از فاز ۴
**شاخه جاری:** `phase/4-publishing`
**آخرین کامیت:** `8303c6b` — test(publishing)

---

## ۱. فاز جاری و پیشرفت

| فاز | موضوع | وضعیت | درصد |
|-----|--------|--------|------|
| 0a | زیرساخت (Docker, CI, pre-commit) | ✅ کامل | 100% |
| 1 | Bootstrap (Django scaffold, 12 اپ، core/accounts/agencies) | ✅ کامل | 100% |
| 2 | listings + crm (مدل، سرویس، view، template) | ✅ کامل | 100% |
| 3 | Matching engine + Dashboard واقعی | ✅ کامل | 100% |
| **4** | **Publishing (انتشار به پورتال‌ها)** | **✅ کامل** | **100%** |
| 5 | SMS / OTP واقعی | ⬜ شروع نشده | 0% |

---

## ۲. آنچه کامل و تست‌شده است

### زیرساخت (فاز 0a / 1 / 2 / 3 — ثابت، تغییر نشده)
- Docker Compose، CI، pre-commit، Makefile، ara.ps1
- core/accounts/agencies/listings/crm/matching — کامل‌شده در فازهای قبل

### اپ `publishing` — جدید در فاز ۴

#### مدل‌ها
- [`apps/publishing/models.py`](../apps/publishing/models.py)
  - `Portal` choices: dummy, divar, sheypoor
  - `JobStatus` choices: pending / running / success / failed
  - `PortalConfig` — کانفیگ پورتال برای هر آژانس (credentials رمزنگاری‌شده)
  - `PublishJob` — هر بار ارسال به پورتال (agency, listing, portal_config, status, external_id, ...)

#### Adapter pattern
- [`apps/publishing/adapters.py`](../apps/publishing/adapters.py)
  - `BasePortalAdapter` — کلاس پایه
  - `DummyAdapter` — همیشه موفق؛ برای dev/test
  - `ADAPTER_MAP` — رجیستری adapter‌ها
  - `get_adapter(portal)` — برگرداندن adapter مناسب

#### سرویس و task
- [`apps/publishing/services.py`](../apps/publishing/services.py) — `publish_listing(listing_id, config_id)`
- [`apps/publishing/tasks.py`](../apps/publishing/tasks.py) — `publish_listing_task` (Celery, max_retries=3)

#### UI
- [`apps/publishing/views.py`](../apps/publishing/views.py) — `ListingPublishJobListView`, `PublishCreateView`
- [`apps/publishing/urls.py`](../apps/publishing/urls.py) — `/publishing/listings/<pk>/jobs/`
- [`templates/publishing/publish_job_list.html`](../templates/publishing/publish_job_list.html)
- [`templates/listings/detail.html`](../templates/listings/detail.html) — دکمه «انتشار در پورتال‌ها» اضافه شد

#### داشبورد
- [`apps/dashboard/views.py`](../apps/dashboard/views.py) — کارت ششم: `published_today`
- [`templates/dashboard/home.html`](../templates/dashboard/home.html) — ۶ کارت آماری

### تست‌ها (72 passing)

| فایل | تعداد | نیاز به PostGIS |
|------|-------|----------------|
| `tests/test_otp.py` | 9 | خیر |
| `tests/test_listings_nogis.py` | 10 | خیر |
| `tests/test_crm_nogis.py` | 8 | خیر |
| `tests/test_matching_nogis.py` | 13 | خیر |
| `tests/test_publishing_nogis.py` | **12** | خیر |
| `tests/test_core_currency.py` | 16 | خیر |
| `tests/test_encrypted_field.py` | 4 | خیر |
| `tests/test_listings_isolation.py` | 3 | **بله** |
| `tests/test_crm_isolation.py` | 2 | **بله** |

---

## ۳. آنچه نیمه‌کاره است

### ۳.۱ Adapter‌های واقعی (Divar, Sheypoor)
`DummyAdapter` پیاده‌سازی شده اما adapter‌های واقعی (Divar, Sheypoor) نیاز به مستندات API رسمی دارند.
نقطه افزودن:
```python
# apps/publishing/adapters.py
ADAPTER_MAP = {
    "dummy": DummyAdapter,
    "divar": DivarAdapter,   # ← بعد از خواندن مستندات رسمی
}
```

### ۳.۲ آپلود تصویر (ListingImage)
مدل `ListingImage` ساخته شده اما endpoint آپلود فایل وجود ندارد.

### ۳.۳ Tailwind CSS
از Tailwind compile نشده — CSS متغیرها در `static/css/main.css` موجودند.

### ۳.۴ SMS integration
`accounts/tasks.py` stub است (فاز ۵).

### ۳.۵ اپ‌های stub
اپ‌های `messaging`, `ai`, `rendering`, `accounting` فقط stub هستند.

---

## ۴. تصمیم‌های معماری

### ✅ تصمیم‌های گرفته‌شده (فاز ۴)

| تصمیم | دلیل |
|--------|-------|
| Adapter pattern برای portal‌ها | افزودن portal جدید فقط با یک کلاس جدید |
| DummyAdapter در MVP | real API docs لازم است — never guess endpoints |
| `PublishJob.agency` denormalized | فیلتر tenant-scoped بدون JOIN |
| `credentials` رمزنگاری با EncryptedCharField | API token هرگز plain-text در DB |
| Celery task با max_retries=3 | شبکه و خطای موقت retry می‌شود |
| `publish_listing()` service مستقل از view | view فقط dispatch می‌کند |

### ✅ تصمیم‌های گرفته‌شده (فازهای قبل — بدون تغییر)
→ در HANDOFF قبلی مستند شده

---

## ۵. تله‌ها و نکته‌های محیطی

| موضوع | جزئیات |
|--------|---------|
| **Python** | 3.13.0 |
| **Django** | 5.2 LTS |
| **GDAL** | روی Windows نصب نیست — همه تست‌های GIS فقط در Docker/CI |
| **Fernet key** | `testing_nogis.py` = `_Rb6cmq4gjE2pZRi7BalzwZb49Amh9s0NGmxP0dbyW4=` |
| **pytest default DS** | `ara_amlak.settings.testing` (PostGIS) — برای local باید `--ds=ara_amlak.settings.testing_nogis` |
| **Celery در dev** | `publish_listing_task.delay()` بدون worker run نمی‌شود — از `.\ara.ps1 up` استفاده کن |
| **`&&` در PowerShell** | کار نمی‌کند — از `;` یا `if ($?) { ... }` |

---

## ۶. وضعیت گیت

```
شاخه:      phase/4-publishing
origin:    pending push
Working tree: clean
```

### کامیت‌های فاز ۴
```
8303c6b  test(publishing): add 12 no-GIS publishing tests
81be505  feat(dashboard): add published_today stat card
f41a185  feat(publishing): add publish job list view, urls, template, listing link
001ab8c  feat(publishing): add admin for PortalConfig and PublishJob
c1d5931  feat(publishing): add adapter pattern, publish service, and celery task
e1a737f  feat(publishing): add PortalConfig and PublishJob models
```

### شاخه‌های remote
```
origin/phase/4-publishing  ← جاری (پس از push)
origin/phase/3-matching-dashboard
origin/phase/2-listings-crm
origin/phase/1-bootstrap
origin/phase/0a-scaffold
```

---

## ۷. قدم‌های بعدی (به ترتیب اولویت)

### فاز ۵ — SMS / OTP واقعی
- خواندن مستندات ارائه‌دهنده SMS ایرانی (فراسمس، کاوه‌نگار، ...)
- پیاده‌سازی `accounts/tasks.py` واقعی
- OTP تست واقعی (در حال حاضر debug OTP در terminal نمایش داده می‌شود)

### بهبودهای کوتاه‌مدت
- آپلود تصویر برای `ListingImage`
- Adapter‌های واقعی Divar و Sheypoor (پس از خواندن مستندات)
- `property_types` JSONField widget در CRM form → MultipleChoice

---

## ۸. دستورهای اجرا و تست

### تست local (بدون Docker)
```powershell
# تست no-GIS (همه باید سبز باشند — 72 passed)
python -m pytest --ds=ara_amlak.settings.testing_nogis `
  tests/test_core_currency.py `
  tests/test_encrypted_field.py `
  tests/test_otp.py `
  tests/test_listings_nogis.py `
  tests/test_crm_nogis.py `
  tests/test_matching_nogis.py `
  tests/test_publishing_nogis.py `
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
# فایل ملک → انتشار: /publishing/listings/<pk>/jobs/
```

### تست کامل (Docker — PostGIS لازم دارد)
```powershell
.\ara.ps1 up
.\ara.ps1 test
.\ara.ps1 lint
```

---

*این فایل را در ابتدای هر جلسه بخوان. قبل از شروع کد، `git status` و آخرین تست را اجرا کن.*
