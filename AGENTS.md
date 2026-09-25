# AGENTS.md — آرا املاک

## codebase-memory-mcp — قواعد استفاده

این پروژه از `codebase-memory-mcp` برای نگهداری گراف دانش استفاده می‌کند.
**همیشه** ابزارهای گراف MCP را بر grep/glob/file-search ترجیح بده.

نام پروژه در گراف: **`I-amlak`**

مستندات کامل: [`docs/code-intelligence.md`](docs/code-intelligence.md)

---

### قانون ۱ — شروع هر تسک
```
get_architecture(aspects=['all'])     ← فهم کلی
search_graph(name_pattern="...")      ← پیدا کردن محل کد
get_code_snippet(qualified_name="...") ← خواندن کد، نه کل فایل
```

### قانون ۲ — قبل از تغییر امضای تابع یا مدل
```
trace_path(function_name="...", direction="inbound")
```
callerها را قبل از تغییر بررسی کن.

### قانون ۳ — قبل از commit
```
detect_changes(project="I-amlak")
```
تست اپ‌های تأثیرپذیر را اجرا کن.

### قانون ۴ — قبل از اعتماد به نتیج
```
index_status(project="I-amlak")
```
اگر کهنه بود: `index_repository(repo_path="I:\\amlak")`

### قانون ۵ — ادعای «کد مرده»
فقط با تأیید مستقیم از منبع. گراف ارجاع‌های رشته‌ای (URL name، Celery task، signal، template tag، getattr) را نمی‌بیند.
```
check_index_coverage(project="I-amlak", paths=["path/to/file.py"])
```

### قانون ۶ — تصمیم معماری مهم
```
manage_adr(project="I-amlak", mode="set_sections", section_updates={...})
```

### قانون ۷ — گراف جایگزین خواندن کد نیست
قبل از ویرایش، فایل را با `get_code_snippet` یا `read_file` بخوان.

---

## قرارهای پروژه

- **شاخه‌ها:** `phase/<number>-<desc>` از main تازه
- **کامیت‌ها:** Conventional Commits + فوتر `Phase: <number>`
- **تست‌ها:** قبل از هر push سبز باشند
- **Lint:** `ruff check .` پاک باشد
- **اسرار:** هرگز در کد یا لاگ؛ فقط رمزنگاری‌شده در DB یا env
- **Migration:** هر تغییر schema = migration + test
- **Celery:** هر کار خارجی یا طولانی فقط از طریق task
