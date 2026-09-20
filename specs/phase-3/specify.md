# Phase 3 — Specify

## محدوده
فاز ۳ شامل سه حوزه است:

### ۳.۱ Bug Fixes فوری (قبل از هر چیز)
- **LOGIN_URL** — اضافه کردن `LOGIN_URL = "/auth/login/"` به `settings/base.py`
- **detail.html status choices** — اضافه کردن `get_status_choices` به `Listing` یا pass از context

### ۳.۲ Matching Engine
اپ `matching` که برای هر درخواست (Request)، فایل‌های (Listing) منطبق را پیدا می‌کند.

**ورودی:** یک `Request` (agency-scoped)
**خروجی:** لیست `Match` بر اساس امتیاز نزولی

**فیلترهای اجباری (hard filters — عدم تطابق = حذف کامل):**
- `deal_type` یکسان
- `status = active`
- `agency` یکسان (tenant isolation)

**فیلترهای نرم (soft filters — کاهش امتیاز در صورت عدم تطابق):**
- `city` یکسان → +۳۰ امتیاز
- `property_type` در `property_types` درخواست → +۲۵ امتیاز
- `area` در بازه `[min_area, max_area]` → +۲۰ امتیاز
- قیمت در بازه بودجه → +۱۵ امتیاز (بر اساس `deal_type`)
- تعداد اتاق در بازه → +۱۰ امتیاز

**مدل Match:**
```
Match(request FK, listing FK, score INT, created_at)
unique_together: (request, listing)
```

**Celery Task:**
- بعد از ثبت هر درخواست جدید، matching اجرا شود
- Signal `post_save` روی `Request` → task `run_matching_for_request`
- نتایج با `score > 0` ذخیره شوند

**UI:**
- در صفحه detail درخواست، لیست match‌های مرتب‌شده بر اساس score نمایش داده شود
- در صفحه detail فایل، لیست درخواست‌های match نمایش داده شود

### ۳.۳ Dashboard واقعی
کارت‌های آماری برای آژانس:
- تعداد فایل‌های active
- تعداد درخواست‌های جدید (status=new)
- تعداد match‌های امروز
- تعداد کل فایل‌ها و درخواست‌ها

## خارج از محدوده این فاز
- Publishing (پورتال‌ها) — فاز ۴
- SMS واقعی — فاز ۵
- آپلود تصویر — فاز ۲.۵
