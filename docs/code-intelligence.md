# Code Intelligence — آرا املاک

## نام پروژه در گراف

```
I-amlak
```

(CBM نام پروژه را از مسیر ریشه می‌سازد: `I:\amlak` → `I-amlak`)

## وضعیت گراف

| فیلد | مقدار |
|------|-------|
| پروژه | `I-amlak` |
| نسخه CBM | 0.11.0 |
| تعداد node | 612 |
| تعداد edge | 2094 |
| وضعیت | `ready` |
| ایندکس‌شده در | 2026-09-20 |

## نصب

باینری در مسیر زیر نصب شده:
```
C:\Users\acer\AppData\Local\Programs\codebase-memory-mcp\codebase-memory-mcp.exe
```

PATH کاربر به‌روز شده؛ دستور کوتاه: `codebase-memory-mcp`

## دستورهای پرکاربرد

```powershell
# بررسی وضعیت ایندکس
codebase-memory-mcp cli index_status --project=I-amlak

# فهرست پروژه‌ها
codebase-memory-mcp cli list_projects

# جستجوی تابع/کلاس
codebase-memory-mcp cli search_graph --project=I-amlak --name-pattern=".*format_toman.*"

# مسیر فراخوانی (ببین چه کسی این تابع را صدا می‌زند)
codebase-memory-mcp cli trace_path --project=I-amlak --function-name=verify_otp --direction=inbound

# خواندن کد یک تابع مشخص (به‌جای خواندن کل فایل)
codebase-memory-mcp cli get_code_snippet --project=I-amlak --qualified-name="I-amlak.apps.core.currency.format_toman"

# بررسی پوشش ایندکس
codebase-memory-mcp cli check_index_coverage --project=I-amlak --paths="apps/core/currency.py"

# تغییرات تأثیرگذار قبل از کامیت
codebase-memory-mcp cli detect_changes --project=I-amlak

# Cypher query مستقیم (مثال: توابع بدون فراخوانی‌کننده)
codebase-memory-mcp cli query_graph --project=I-amlak --query="MATCH (f:Function) WHERE NOT EXISTS { (f)<-[:CALLS]-() } RETURN f.name LIMIT 20"

# ریندکس کردن (پس از تغییرات بزرگ)
codebase-memory-mcp cli index_repository --repo-path=I:\amlak
```

## باز کردن UI گراف (تعاملی)

```powershell
codebase-memory-mcp --ui=true --port=9749
```

سپس در مرورگر باز کنید:

**http://localhost:9749**

daemon در پس‌زمینه اجرا می‌شود؛ تنها یک سرور HTTP برای همه session‌ها.

## شروع/توقف daemon

```powershell
codebase-memory-mcp daemon start   # شروع daemon دائمی
codebase-memory-mcp daemon stop    # توقف daemon
```

## قواعد استفاده برای ایجنت‌ها

> این قواعد در [`AGENTS.md`](../AGENTS.md) نیز آمده است.

### ۱. شروع هر تسک
قبل از هر کار:
```
get_architecture(aspects=['all'])   ← فهم کلی معماری
search_graph(name_pattern="...")    ← پیدا کردن محل کد
```
به‌جای خواندن کل فایل، از `get_code_snippet` استفاده کن.

### ۲. قبل از تغییر امضای تابع یا مدل
```
trace_path(function_name="...", direction="inbound")
```
callerهای فعلی را ببین تا regression ایجاد نشود.

### ۳. قبل از commit
```
detect_changes(project="I-amlak")
```
دامنه اثر را بررسی کن. تست اپ‌های تأثیرپذیر را اجرا کن.

### ۴. قبل از اعتماد به نتایج گراف
```
index_status(project="I-amlak")
```
اگر کهنه بود: `index_repository(repo_path="I:\\amlak")`

### ۵. ادعای «کد مرده» یا «بی‌استفاده»
فقط با تأیید مستقیم از منبع. تحلیل ایستا ارجاع‌های رشته‌ای (نام URL، نام تسک Celery، signal، template tag، getattr) را نمی‌بیند.
```
check_index_coverage(project="I-amlak", paths=["path/to/file.py"])
```

### ۶. تصمیم معماری مهم جدید
```
manage_adr(project="I-amlak", mode="set_sections", section_updates={...})
```

### ۷. گراف جایگزین خواندن کد نیست
قبل از ویرایش، فایل را با `get_code_snippet` یا `read_file` بخوان.

## محدودیت‌های شناخته‌شده query «کد مرده»

نتیجه‌ی query زیر:
```cypher
MATCH (f:Function) WHERE NOT EXISTS { (f)<-[:CALLS]-() } RETURN f.name LIMIT 20
```

**۲۰ تابع بدون فراخوانی‌کننده (در گراف):**
`print, toman_filter, fa_number_filter, fa_format_filter, login_view, otp_verify_view, logout_view, send_otp_sms_task, home_view, app, toggleDark, ui_context, agency_a, agency_b, user_a, user_b, superadmin`

**تفسیر مهم:**
- `login_view`, `home_view`, `logout_view` — از طریق `urls.py` (رشته URL) فراخوانی می‌شوند، نه import مستقیم. گراف ایستا این را نمی‌بیند.
- `send_otp_sms_task` — Celery task است؛ فراخوانی از طریق `.delay()` که رشته نام task است.
- `toman_filter`, `fa_number_filter`, `fa_format_filter` — template tags هستند؛ از template HTML صدا زده می‌شوند.
- `app`, `toggleDark` — توابع Alpine.js در JavaScript هستند.
- `agency_a`, `agency_b`, `user_a`, `user_b`, `superadmin` — pytest fixtures هستند؛ توسط framework تزریق می‌شوند.
- هیچ‌کدام از این‌ها واقعاً «مرده» نیستند.

## فایل .cbmignore

در ریشه پروژه قرار دارد. دایرکتوری‌های بی‌فایده ایندکس نمی‌شوند:
```
staticfiles/
media/
node_modules/
htmlcov/
static/vendor/
*.min.js
*.min.css
```

## آرتیفکت گراف و git

آرتیفکت گراف (`.codebase-memory/`) در `.gitignore` است و کامیت **نمی‌شود** (هر توسعه‌دهنده گراف محلی خود را می‌سازد). طبق بخش «Team-Shared Graph Artifact» در README رسمی، به اشتراک‌گذاری از طریق Git LFS نیاز به بررسی هزینه دارد.
