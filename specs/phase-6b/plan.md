# Phase 6B — Poster Persian Font (self-contained) Plan

## هدف

پوستر در محیط Docker (لینوکس بدون فونت فارسی) درست رندر شود — Vazirmatn
به‌صورت base64 داخل خود HTML پوستر جاسازی می‌شود (بدون هیچ درخواست خارجی).

## روش

- فونت‌های self-hosted موجود در `static/fonts/` خوانده و به data URI تبدیل می‌شوند:
  Regular (400)، Bold (700)، ExtraBold (800) — هر کدام ~۵۰KB → ~۲۰۰KB پایه،
  ~۲۷۰KB base64 در HTML (قابل قبول برای یک رندر job).
- یافتن فایل با `django.contrib.staticfiles.finders.find` (سازگار با
  collectstatic/whitenoise و dev).
- اگر فایل نبود → @font-face اصلاً تزریق نمی‌شود و fallback سیستمی کار می‌کند
  (پوستر هرگز به‌خاطر فونت fail نمی‌کند).

## تغییرات

- `apps/rendering/services.py` — `_font_data_uris()` + سه کلید context
- `templates/rendering/poster.html` — سه @font-face شرطی

## تست‌ها

- HTML پوستر شامل `@font-face` و `data:font/woff2;base64,`
- بدون فایل فونت (mock) → بدون @font-face، رندر ادامه می‌یابد
- رندر واقعی Playwright همچنان سبز (تست‌های 6A)
