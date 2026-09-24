# Phase 5A + 5B — Voice Entry / Smart Draft Plan

## هدف

ثبت هوشمند فایل ملک با صدا — MVP اصلی پروژه:

- مشاور دکمه ضبط را می‌زند، توضیحات فایل را می‌گوید
- صدا آپلود و **رونویسی** (transcribe) می‌شود (Whisper یا Gemini)
- از متن رونویسی، **پیش‌نویس فایل** به‌صورت ساختاریافته استخراج می‌شود
- با یک کلیک، پیش‌نویس به یک فایل ملک (Listing با status=draft) تبدیل می‌شود

## معماری

الگوی provider (مشابه `apps/messaging/providers`) با دو ABC:

```
apps/ai/
├── models.py            ← AgencyAIConfig, VoiceNote, VoiceDraft
├── providers/
│   ├── base.py          ← TranscriptionProvider ABC, TranscriptionResult
│   ├── console.py       ← ConsoleTranscriptionProvider (dev/test)
│   ├── openai_whisper.py← POST /v1/audio/transcriptions (multipart)
│   └── gemini.py        ← POST /v1beta/interactions (JSON, base64 audio)
├── services.py          ← create_voice_note, enqueue/run_transcription
├── draft_parser.py      ← parse_listing_transcript (تابع خالص، رجکس فارسی)
├── tasks.py             ← transcribe_voice_task (backoff)
├── views.py             ← آپلود HTMX، لیست، جزئیات، تولید/اعمال پیش‌نویس
├── urls.py              ← /ai/voice/...
├── admin.py
└── migrations/0001_initial.py
```

## مستندات رسمی (مطالعه‌شده — قانون §10)

| سرویس | Endpoint | پارامترها | پاسخ |
|-------|----------|-----------|------|
| OpenAI | `POST https://api.openai.com/v1/audio/transcriptions` | multipart: `file`, `model` (whisper-1), `language` (fa) — حداکثر 25MB | `{"text": "..."}` |
| Gemini | `POST https://generativelanguage.googleapis.com/v1beta/interactions` | هدر `x-goog-api-key`؛ JSON: `input: [{type:"text"},{type:"audio", data: base64, mime_type}]` — inline حداکثر 20MB | `output_text` |

## مدل‌ها

### AgencyAIConfig
```
agency      FK → Agency
provider    CharField: openai / gemini / console
api_key     EncryptedCharField  ← رمزنگاری‌شده
model_name  CharField blank     ← پیش‌فرض هر provider
is_active   BooleanField
```

### VoiceNote — ماشین وضعیت
```
uploaded → queued → transcribing → transcribed
                        ↘ failed
```
```
agency, listing (FK nullable), audio (FileField), original_filename,
mime_type, file_size, duration_seconds, language="fa",
status, transcript (TextField), provider, provider_file_id,
error_message, transcribed_at, uploaded_by
```

### VoiceDraft
```
agency, voice_note (OneToOne), data (JSONField)، missing (JSONField),
confidence (FloatField), listing (FK nullable — فایل ساخته‌شده),
status: draft / applied
```

## پارس فارسی (draft_parser.py — تابع خالص)

ورودی: متن رونویسی نرمال‌شده (`normalize_fa`) — خروجی: dict فیلدها + `missing` + `confidence`

| فیلد | الگو |
|------|------|
| متراژ | `(\d+)\s*متر` |
| اتاق/خواب | `(\d+)\s*(اتاق|خواب)` + اعداد حرفی (دوخوابه…) |
| طبقه / کل | `طبقه\s*(\d+)`، `(\d+)\s*طبقه` |
| سال ساخت | `ساخت\s*(\d{2,4})` شمسی → میلادی (−621) |
| قیمت فروش | `(\d+)\s*(میلیارد|میلیون)\s*تومان` |
| رهن/اجاره | `رهن\s*(\d+)`، `اجاره\s*(\d+)` |
| امکانات | پارکینگ، آسانسور، انباری، بالکن (و «بدون X») |
| نوع ملک | آپارتمان/ویلایی/زمین/مغازه/دفتر/بازار |
| جهت | شمالی/جنوبی/شرقی/غربی |
| محله | `محله‌ی? ([\u0600-\u06FF ]+)` — سپس resolve به Neighborhood |

LLM provider برای 5B بعداً (فاز AI کامل) اضافه می‌شود؛ پیش‌فرض فعلی parser قطعی
رجکسی است که آفلاین و در تست کاملاً قابل پیش‌بینی است.

## قواعد رعایت‌شده

- همه کار خارجی (Whisper/Gemini) فقط از طریق Celery task — قانون §5
- API key با EncryptedCharField — هرگز در لاگ
- هر مدل tenant-scoped با AgencyOwned + تست isolation
- آپلود صوت: محدودیت 25MB و MIME سفید‌فهرست + بررسی جادویی (magic bytes)
- اعداد قیمت فقط BigInteger تومان
