# Phase 5A + 5B — Tasks

## Task 5-0: شاخه + اسپک
- [x] `git checkout -b phase/5a-voice-entry` (از phase/4ab-sms-notification)
- [x] `specs/phase-5/plan.md`
- [x] Commit: `docs(specs): record phase 5 plan`

## Task 5-1: مدل‌ها + migration + admin
- [x] `apps/ai/models.py` — AgencyAIConfig, VoiceNote (state machine), VoiceDraft
- [x] `apps/ai/migrations/0001_initial.py`
- [x] `apps/ai/admin.py`
- [x] Commit: `feat(ai): add AgencyAIConfig, VoiceNote and VoiceDraft models`

## Task 5-2: providerهای رونویسی
- [x] `apps/ai/providers/base.py` — TranscriptionProvider ABC + TranscriptionResult
- [x] `apps/ai/providers/console.py` — ConsoleTranscriptionProvider
- [x] `apps/ai/providers/openai_whisper.py` — (mocked-HTTP tested)
- [x] `apps/ai/providers/gemini.py` — (mocked-HTTP tested)
- [x] Commit: `feat(ai): add transcription provider adapters`

## Task 5-3: سرویس + Celery task
- [x] `apps/ai/services.py` — create_voice_note (اعتبارسنجی)، enqueue/run_transcription
- [x] `apps/ai/tasks.py` — transcribe_voice_task با exponential backoff
- [x] Commit: `feat(ai): add voice note service and transcription task`

## Task 5-4: Views + URLs + Templates (5A)
- [x] `apps/ai/views.py` — upload (HTMX), list, status partial
- [x] `apps/ai/urls.py` + include در `ara_amlak/urls.py`
- [x] `templates/ai/voice_note_list.html`, `partials/voice_note_item.html`
- [x] بخش صوت در `templates/listings/detail.html` + لینک ناوبری
- [x] Commit: `feat(ai): add voice upload views and templates`

## Task 5-5: تست‌های 5A
- [x] `tests/test_5a_voice_transcription.py`
- [x] Commit: `test(ai): add voice transcription tests`

## Task 5-6: پارس فارسی + پیش‌نویس (5B)
- [x] `apps/ai/draft_parser.py` — parse_listing_transcript (تابع خالص)
- [x] `apps/ai/services.py` — extract_draft + apply_draft_to_listing
- [x] Commit: `feat(ai): add Persian transcript parser and draft service`

## Task 5-7: Views/Templates پیش‌نویس (5B)
- [x] جزئیات VoiceNote + تولید پیش‌نویس + اعمال به فایل
- [x] Commit: `feat(ai): add draft detail, generate and apply views`

## Task 5-8: تست‌های 5B
- [x] `tests/test_5b_smart_draft.py`
- [x] Commit: `test(ai): add smart draft parser and apply tests`

## Task 5-9: Cleanup + Docs
- [x] `ruff check .` → پاک
- [x] pytest کامل → سبز
- [x] `docs/HANDOFF.md` به‌روزرسانی
- [x] Commit: `docs(specs): update HANDOFF after phase 5A+5B`
- [x] `git push -u origin phase/5a-voice-entry`
