# HANDOFF — آرا املاک / Ara Amlak

**آخرین به‌روزرسانی:** پس از تکمیل فاز 6A — رندر واقعی پوستر PDF/PNG با Playwright
**شاخه جاری:** `phase/6a-poster-render`
**آخرین کامیت:** پس از کامیت docs این جلسه

---

## ۱. فاز جاری و پیشرفت

| فاز | موضوع | وضعیت | درصد |
|-----|--------|--------|------|
| 0A | زیرساخت (Docker, CI, pre-commit) | ✅ کامل | 100% |
| 0B | دیزاین‌سیستم Apple-style | ⚠️ نسبی | 60% |
| 0C | هویت کاربر، نقش‌ها، AuditLog، دعوت عضو | ✅ کامل | 100% |
| 1A | مدل داده فایل (City/Neighborhood/Feature) | ✅ کامل | 100% |
| 1B | صفحات CRUD فایل | ✅ کامل | 100% |
| 1C | رسانه (آپلود، پردازش، سند خصوصی) | ✅ کامل | 100% |
| 1D | جستجو، فیلتر، normalize_fa، ImportJob | ✅ کامل | 100% |
| 2A | مخاطبین، درخواست‌ها، رضایت پیامک | ✅ کامل | 100% |
| 2B | تایم‌لاین، بازدید، وظایف، اعلان‌ها | ✅ کامل | 100% |
| 3 | Matching engine + Dashboard | ✅ کامل | 100% |
| 4 (publishing) | Publishing به پورتال‌ها | ✅ کامل | 100% |
| 4A | زیرساخت پیامک (Kavenegar, MeliPayamak, Console) | ✅ کامل | 100% |
| 4B | ارسال خودکار تطبیق، فرم عمومی، لغو، تمدید | ✅ کامل | 100% |
| **5A** | **زیرساخت صدا (Whisper/Gemini/Console) + رونویسی** | **✅ کامل** | **100%** |
| **5B** | **پارسر فارسی + پیش‌نویس هوشمند فایل از رونویسی** | **✅ کامل** | **100%** |
| **6A** | **رندر واقعی پوستر PDF/PNG (Playwright)** | **✅ کامل** | **100%** |
| 7–11 | انتشار واقعی، حسابداری، AI کامل، ... | ⬜ شروع نشده | 0% |

---

## ۲. آنچه در این جلسه کامل شد

### فاز 5A — زیرساخت صدا

- **[`apps/ai/models.py`](../apps/ai/models.py)** — `AgencyAIConfig` (کلید رمزنگاری‌شده)، `VoiceNote` (ماشین وضعیت: uploaded → queued → transcribing → transcribed/failed)، `VoiceDraft`
- **[`apps/ai/providers/base.py`](../apps/ai/providers/base.py)** — `TranscriptionProvider` ABC + `TranscriptionResult`
- **[`apps/ai/providers/console.py`](../apps/ai/providers/console.py)** — رونویسی ساختگی قطعی برای dev/test (متن نمونه فارسی)
- **[`apps/ai/providers/openai_whisper.py`](../apps/ai/providers/openai_whisper.py)** — `POST /v1/audio/transcriptions` (multipart، مدل whisper-1، پارامتر language)
- **[`apps/ai/providers/gemini.py`](../apps/ai/providers/gemini.py)** — `POST /v1beta/interactions` (هدر x-goog-api-key، صوت base64 + mime_type، پاسخ output_text، سقف inline)
- **[`apps/ai/services.py`](../apps/ai/services.py)** — `create_voice_note` (اعتبارسنجی magic bytes + سقف 20MB)، `enqueue_transcription`، `run_transcription`
- **[`apps/ai/tasks.py`](../apps/ai/tasks.py)** — `transcribe_voice_task` با exponential backoff (60s پایه، ۵ بار)
- Views/URLs: `/ai/voice/` (لیست + آپلود)، `upload/`، `<pk>/status/` (polling HTMX)، `<pk>/retry/`، `<pk>/`
- بخش «یادداشت صوتی» در صفحه جزئیات فایل + لینک ناوبری «🎙️ ثبت با صدا»
- Migration: `ai/0001_initial`

### فاز 5B — پیش‌نویس هوشمند

- **[`apps/ai/draft_parser.py`](../apps/ai/draft_parser.py)** — `parse_listing_transcript()` تابع خالص: متراژ، اتاق/خواب (رقمی/حرفی/چسبیده)، طبقه و طبقات کل («طبقه سوم از پنج طبقه»)، سال ساخت شمسی→میلادی (−621)، قیمت (رقمی/حرفی/مرکب «یک میلیارد و دویست میلیون»، رهن/اجاره از context)، امکانات با نقیض («بدون پارکینگ»)، نوع ملک، جهت، محله؛ خروجی data + missing (وابسته به deal_type) + confidence
- **کلاس حروف فارسی `_FA`** بدون علائم (، ؛) تا توکن‌ها به کاما نچسبند — دام کلاس `[\u0600-\u06FF]`
- **[`apps/ai/services.py`](../apps/ai/services.py)** — `extract_draft()` (idempotent، resolve محله به Neighborhood با نادیده‌گرفتن فاصله/ZWNJ)، `apply_draft_to_listing()` (ساخت Listing با status=draft + کد خودکار + اتصال به VoiceNote/VoiceDraft)
- Views: `draft_generate` (HTMX)، `draft_apply` (redirect به فرم ویرایش فایل)
- Template: `partials/draft_fields.html` (جدول فیلدها + فیلدهای نایافته + دکمه ساخت فایل)
- **۶۹ تست جدید** در `tests/test_5a_voice_transcription.py` (43) و `tests/test_5b_smart_draft.py` (26)

### فاز 6A — رندر پوستر (واقعی، نه stub)

- **[`apps/rendering/models.py`](../apps/rendering/models.py)** — `RenderJob` (ماشین وضعیت pending → running → success/failed، مشابه PublishJob)
- **[`apps/rendering/engines.py`](../apps/rendering/engines.py)** — `BaseRenderEngine` ABC، `PlaywrightRenderEngine` (chromium headless → `page.pdf(format="A4")` یا `page.screenshot`)، `StubRenderEngine` (فقط dev/test بدون مرورگر)؛ انتخاب با `RENDER_BACKEND` (پیش‌فرض playwright، fallback خودکار به stub اگر playwright نصب نباشد)
- **[`apps/rendering/services.py`](../apps/rendering/services.py)** — `render_poster_html` (پوستر self-contained: عکس شاخص و لوگو به‌صورت base64 data URI — بدون وابستگی خارجی)، `enqueue_render`، `run_render`
- **[`apps/rendering/tasks.py`](../apps/rendering/tasks.py)** — `render_poster_task` با exponential backoff
- قالب: `templates/rendering/poster.html` (RTL، Apple-style، `format_toman` برای قیمت، ارقام فارسی)، `render_job_list.html` + پارشیال با polling HTMX
- Views/URLs: `/rendering/listings/<pk>/jobs/` (لیست + رندر PDF/PNG)، `create/`، `jobs/<pk>/download/` (FileResponse scoped)، `jobs/<pk>/status/`
- لینک «پوستر PDF» در Actions صفحه جزئیات فایل
- Migration: `rendering/0001_initial`
- **۲۵ تست جدید** در `tests/test_6a_rendering.py` — شامل **دو تست رندر واقعی Playwright** (PDF واقعی > 1KB و PNG واقعی؛ skipif وقتی Chromium نباشد)

---

## ۳. تست‌ها (365 passing — بدون PostGIS)

| فایل | تعداد |
|------|-------|
| `tests/test_otp.py` | 9 |
| `tests/test_listings_nogis.py` | 10 |
| `tests/test_crm_nogis.py` | 8 |
| `tests/test_matching_nogis.py` | 13 |
| `tests/test_publishing_nogis.py` | 12 |
| `tests/test_core_currency.py` | 16 |
| `tests/test_encrypted_field.py` | 4 |
| `tests/test_0c_roles_audit_invite.py` | 18 |
| `tests/test_1a_geo_models.py` | 16 |
| `tests/test_2a_contact_consent.py` | 16 |
| `tests/test_1c_media.py` | 19 |
| `tests/test_1d_search_import.py` | 38 |
| `tests/test_2b_timeline_visit_tasks.py` | 26 |
| `tests/test_4ab_sms_notification.py` | 53 |
| `tests/test_5a_voice_transcription.py` | **43** |
| `tests/test_5b_smart_draft.py` | **26** |
| `tests/test_6a_rendering.py` | **25** |
| **جمع** | **365** |

---

## ۴. آنچه نیمه‌کاره است

### ۴.۱ فازهای بعدی (اولویت‌بندی)
1. **7A** — انتشار واقعی به پورتال‌ها (adapterهای Divar/Sheypoor)
2. LLM draft provider — استخراج پیش‌نویس با Gemini (فعلاً پارسر رجکسی قطعی)
3. آپلود فایل‌های صوتی بزرگ در Gemini از طریق Files API (فعلاً فقط inline ≤20MB)
4. فونت Vazirmatn embedded در پوستر (فعلاً fallback سیستمی — در Docker فونت فارسی لازم است)

### ۴.۲ موارد نیمه‌کاره
- `test_tenant_isolation.py` — تست‌های pre-existing broken
- `test_health.py` — pre-existing broken
- OTP در تولید باید از `AgencySMSConfig` آژانس استفاده کند (فعلاً Console)
- `openpyxl` برای xlsx import نیاز به نصب جداگانه دارد
- پنل مدیریت AI (AgencyAIConfig) فعلاً فقط از طریق admin
- ضبط مستقیم با MediaRecorder JS — فعلاً input file با capture=microphone (موبایل‌فرندلی)
- پنل مدیریت RenderJob از طریق admin (صفحه اختصاصی در فاز UI)

---

## ۵. تله‌ها و نکته‌های محیطی

| موضوع | جزئیات |
|--------|---------|
| **Python** | 3.13.0 |
| **Django** | 5.2 LTS |
| **GDAL** | روی Windows نصب نیست |
| **Fernet key** | `_Rb6cmq4gjE2pZRi7BalzwZb49Amh9s0NGmxP0dbyW4=` |
| **SMS Provider** | `AgencySMSConfig` با `is_active=True` باید وجود داشته باشد؛ وگرنه Console |
| **AI Provider** | بدون `AgencyAIConfig` فعال → `ConsoleTranscriptionProvider` (متن نمونه قطعی) |
| **سقف صوت** | 20MB (کامپایل با سقف 25MB اوپن‌ای‌آی و سقف inline 20MB جمنای) |
| **build_year** | میلادی در DB؛ پارسر شمسی را −621 می‌کند |
| **ConsentRecord.is_active** | property است، نه فیلد DB — در filter از `revoked_at__isnull=True` استفاده کنید |
| **RequestStatus** | مقادیر: `new`, `in_progress`, `matched`, `closed`, `cancelled`, `expired` — `active` وجود ندارد |
| **Request.expires_at** | `DateTimeField` است نه `DateField` |
| **ContactPhone** | فیلدهای `phone` (encrypted) و `phone_normalized` دارد — `phone_raw` وجود ندارد |
| **ConsentRecord** | به `agency` FK نیاز دارد؛ فیلد `text_version` (نه `consent_text_version`) |
| **URL پیشوند SMS** | `/messaging/` |
| **URL پیشوند AI** | `/ai/` — voice list/upload/status/retry/draft/apply |
| **URL پیشوند Rendering** | `/rendering/` — job list/create/download/status |
| **RENDER_BACKEND** | `playwright` پیش‌فرض (در این محیط Chromium نصب است)؛ `stub` برای محیط بدون مرورگر؛ fallback خودکار اگر playwright import نشود |
| **کاما فارسی** | U+060C داخل رنج `[\u0600-\u06FF]` است — در regex فارسی کلاس حروف بدون علائم (`_FA`) استفاده شود |
| **Celery در تست** | `CELERY_TASK_ALWAYS_EAGER=True` — آپلود صوت و رندر پوستر در تست تا انتها اجرا می‌شوند (رندر واقعی ~۱-۲ ثانیه) |
| **override_settings** | روی کلاس‌های plain pytest کار نمی‌کند — از فیکسچر `settings` استفاده کنید |
| **FieldFile بدون فایل** | `not media_file.file` با ValueError کرش می‌کند — در try/pattern امن بخوانید |
| **dev server** | `python manage.py runserver 8070 --settings=ara_amlak.settings.local_sqlite` |

---

## ۶. وضعیت گیت

- شاخه: `phase/6a-poster-render` (از `phase/5a-voice-entry`)
- پوش شده: ✅

---

## ۷. قدم‌های بعدی به ترتیب

1. فاز 7A — انتشار واقعی به پورتال‌ها (Divar/Sheypoor adapters)
2. LLM provider برای استخراج پیش‌نویس (Gemini structured output)
3. فونت فارسی embedded برای پوستر در Docker

---

## ۸. دستورهای اجرا و تست

```powershell
# تست no-GIS (365 تست)
python -m pytest --ds=ara_amlak.settings.testing_nogis tests/ `
  --ignore=tests/test_tenant_isolation.py `
  --ignore=tests/test_health.py -v

# lint
ruff check .

# dev server (port 8070)
python manage.py runserver 8070 --settings=ara_amlak.settings.local_sqlite
# login: 09000000000 / admin1234
```

---

*این فایل را در ابتدای هر جلسه بخوان. قبل از شروع کد، `git status` و آخرین تست را اجرا کن.*
