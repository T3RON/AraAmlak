# Phase 5C — LLM Draft Extraction (Gemini structured output) Plan

## هدف

تکمیل فاز 5B: استخراج پیش‌نویس فایل از رونویسی با **Gemini structured output**
به‌جای صرفاً پارسر رجکسی. پارسر رجکسی می‌ماند و **fallback** آفلاین است.

## مستندات رسمی (خوانده‌شده ۲۰۲۶-۰۹ — قانون §10)

- https://ai.google.dev/gemini-api/docs/structured-output (Interactions API)

Structured output با REST:
```json
POST https://generativelanguage.googleapis.com/v1beta/interactions
x-goog-api-key
{
  "model": "gemini-2.0-flash",
  "input": "<prompt>",
  "response_format": {
    "type": "text",
    "mime_type": "application/json",
    "schema": { ...JSON Schema... }
  }
}
```
JSON نهایی مستقیماً در `output_text` برمی‌گردد. توصیه رسمی: اعتبارسنجی
مقادیر در سمت اپلیکیشن — ما هم می‌کنیم (نرمال‌سازی سخت‌گیرانه).

## معماری

```
apps/ai/providers/
├── base.py            ← TranscriptionProvider (موجود)
├── draft_base.py      ← DraftProvider ABC (name, is_async, extract)
├── regex_draft.py     ← RegexPersianDraftProvider (wrap پارسر موجود، sync)
└── gemini_draft.py    ← GeminiDraftProvider (external → Celery اجباری)
```

- `get_draft_provider_for_agency(agency)` — config دیوار جمنای با کلید →
  `GeminiDraftProvider`؛ در غیر این صورت regex (رفتار فعلی حفظ می‌شود).
- `extract_draft(voice_note, provider=None)` — پارامتر provider اضافه؛
  `VoiceDraft.parser = provider.name`.
- چون تماس LLM خارجی است (قانون §5): مسیر LLM در ویو **Celery** می‌رود
  (`extract_draft_task`) و partial «در حال استخراج» با polling HTMX؛ مسیر
  regex هم‌چنان همگام (بدون تماس خارجی).
- `draft_status` endpoint جدید برای polling.

## نرمال‌سازی پاسخ LLM (اعتبارسنجی سخت‌گیرانه)

- فقط کلیدهای مجاز لیستینگ حفظ می‌شوند (junk حذف)
- اعداد → int؛ boolean → bool؛ enumها فقط با مقادیر مجاز choices
- `build_year`: اگر ۱۳۰۰–۱۴۹۹ → شمسی، +621 میلادی؛ دو رقمی → ۱۳xx
- booleans در schema از نوع `["boolean","null"]` — null یعنی «ذکر نشده»
- `missing` و `confidence` با `score_draft()` مشترک محاسبه می‌شود

## تست‌ها (mocked HTTP)

- شکل درخواست (URL/هدر/response_format/schema)
- نرمال‌سازی: int، enum نامعتبر حذف، کلید junk حذف، سال شمسی→میلادی
- JSON خراب/بدون متن → خطا
- انتخاب provider (config گمنای با کلید / بدون کلید / بدون config)
- ویو: مسیر async (partial در حال استخراج + dispatch task) و مسیر sync
