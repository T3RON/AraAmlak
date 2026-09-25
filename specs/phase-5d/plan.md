# Phase 5D — In-page Voice Recording (MediaRecorder) Plan

## هدف

مشاور بدون خروج از صفحه، داخل همان فرم ضبط کند — دکمه «ضبط/پایان» با
MediaRecorder API و آپلود خودکار خروجی به همان endpoint موجود.

## روش (سمت کلاینت)

- `navigator.mediaDevices.getUserMedia({audio:true})` → `MediaRecorder`
- mime ترجیحی: `audio/webm` → `audio/ogg` → پیش‌فرض مرورگر
  (هر سه در `ALLOWED_AUDIO_MIMES` هستند؛ magic-detection هم OggS/webm/mp4
  را می‌شناسد — تست 5A)
- پایان ضبط: Blob → File → همان `uploadFile()` موجود (HTMX/fetch)
- خطاها (عدم اجازه میکروفن / عدم پشتیبانی مرورگر): پیام فارسی + مسیر
  انتخاب فایل دستی همچنان برقرار
- تایمر ثانیه در حالت ضبط؛ `prefers-reduced-motion` رعایت (بدون انیمیشن)

سمت سرور هیچ تغییری لازم ندارد.

## تست‌ها (سمت سرور — JS قابل تست Django نیست)

- پارشیال شامل `MediaRecorder`، دکمه ضبط و پیام خطای اجازه
- آپلود فایل با magic bytes واقعی webm → end-to-end تا transcribed
