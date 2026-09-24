# Phase 6A — Poster Render Plan

## هدف

تولید **پوستر PDF (و PNG)** برای هر فایل ملک — قابل چاپ/اشتراک‌گذاری برای مشتری.

برخلاف فاز 4 (stub publishing)، اینجا رندر **واقعی** است:
**Playwright + Chromium** (طبق قانون §1) HTML پوستر را به PDF تبدیل می‌کند.
در محیط‌های بدون مرورگر، یک `StubRenderEngine` جانشین می‌شود.

## معماری

الگوی engine (مشابه providerهای messaging/ai):

```
apps/rendering/
├── models.py        ← RenderJob (ماشین وضعیت، مشابه PublishJob)
├── engines.py       ← BaseRenderEngine ABC, PlaywrightRenderEngine, StubRenderEngine
├── services.py      ← render_poster_html, enqueue_render, run_render
├── tasks.py         ← render_poster_task (backoff)
├── admin.py, views.py, urls.py
└── migrations/0001_initial.py

templates/rendering/
├── poster.html              ← پوستر self-contained (استایل inline، RTL)
├── render_job_list.html
└── partials/render_job_item.html
```

## پوستر self-contained

HTML پوستر هیچ وابستگی خارجی ندارد تا Playwright بدون base_url کار کند:
- عکس شاخص → **base64 data URI** (از Media.is_cover)
- لوگوی آژانس → base64 data URI (اگر باشد)
- استایل inline در خود قالب؛ RTL؛ `format_toman` برای قیمت‌ها

## مدل RenderJob

```
agency, listing FK → related_name="render_jobs"
kind     : poster_pdf / poster_png
status   : pending → running → success / failed
engine   : نام موتور (playwright / stub)
file     : FileField → rendering/<agency_id>/...
error_message, rendered_at, created_at/updated_at
```

## Engines

| Engine | رفتار |
|--------|-------|
| `PlaywrightRenderEngine` | `sync_playwright` → chromium headless → `page.pdf(format="A4")` یا `page.screenshot(png)` |
| `StubRenderEngine` | فقط برای dev/test بدون مرورگر؛ خروجی حداقلی معتبر (`%PDF`/PNG) |

انتخاب موتور: `RENDER_BACKEND` در settings (`playwright` پیش‌فرض، `stub` جایگزین).

## Views / URLs

| مسیر | متد | کار |
|------|-----|-----|
| `/rendering/listings/<pk>/jobs/` | GET | لیست jobهای رندر فایل + دکمه رندر |
| `/rendering/listings/<pk>/jobs/create/` | POST | ساخت job + صف (HTMX یا redirect) |
| `/rendering/jobs/<pk>/download/` | GET | دانلود خروجی (scoped به آژانس) |

+ بخش «پوستر» در صفحه جزئیات فایل.

## قواعد رعایت‌شده

- رندر کار طولانی → فقط از طریق Celery task (قانون §5)
- `RenderJob` tenant-scoped با AgencyOwned + تست isolation
- دانلود خروجی فقط برای همان آژانس
