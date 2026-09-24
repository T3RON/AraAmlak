# Phase 5A + 5B — Tasks

## Task 5-0: شاخه + اسپک
- [ ] `git checkout -b phase/5a-voice-entry` (از phase/4ab-sms-notification)
- [ ] `specs/phase-5/plan.md`
- [ ] Commit: `docs(specs): record phase 5 plan`

## Task 5-1: مدل‌ها + migration + admin
- [ ] `apps/ai/models.py` — AgencyAIConfig, VoiceNote (state machine), VoiceDraft
- [ ] `apps/ai/migrations/0001_initial.py`
- [ ] `apps/ai/admin.py`
- [ ] Commit: `feat(ai): add AgencyAIConfig, VoiceNote and VoiceDraft models`

## Task 5-2: providerهای رونویسی
- [ ] `apps/ai/providers/base.py` — TranscriptionProvider ABC + TranscriptionResult
- [ ] `apps/ai/providers/console.py` — ConsoleTranscriptionProvider
- [ ] `apps/ai/providers/openai_whisper.py` — (mocked-HTTP tested)
- [ ] `apps/ai/providers/gemini.py` — (mocked-HTTP tested)
- [ ] Commit: `feat(ai): add transcription provider adapters`

## Task 5-3: سرویس + Celery task
- [ ] `apps/ai/services.py` — create_voice_note (اعتبارسنجی)، enqueue/run_transcription
- [ ] `apps/ai/tasks.py` — transcribe_voice_task با exponential backoff
- [ ] Commit: `feat(ai): add voice note service and transcription task`

## Task 5-4: Views + URLs + Templates (5A)
- [ ] `apps/ai/views.py` — upload (HTMX), list, status partial
- [ ] `apps/ai/urls.py` + include در `ara_amlak/urls.py`
- [ ] `templates/ai/voice_note_list.html`, `partials/voice_note_item.html`
- [ ] بخش صوت در `templates/listings/detail.html` + لینک ناوبری
- [ ] Commit: `feat(ai): add voice upload views and templates`

## Task 5-5: تست‌های 5A
- [ ] `tests/test_5a_voice_transcription.py`
- [ ] Commit: `test(ai): add voice transcription tests`

## Task 5-6: پارس فارسی + پیش‌نویس (5B)
- [ ] `apps/ai/draft_parser.py` — parse_listing_transcript (تابع خالص)
- [ ] `apps/ai/services.py` — extract_draft + apply_draft_to_listing
- [ ] Commit: `feat(ai): add Persian transcript parser and draft service`

## Task 5-7: Views/Templates پیش‌نویس (5B)
- [ ] جزئیات VoiceNote + تولید پیش‌نویس + اعمال به فایل
- [ ] Commit: `feat(ai): add draft detail, generate and apply views`

## Task 5-8: تست‌های 5B
- [ ] `tests/test_5b_smart_draft.py`
- [ ] Commit: `test(ai): add smart draft parser and apply tests`

## Task 5-9: Cleanup + Docs
- [ ] `ruff check .` → پاک
- [ ] pytest کامل → سبز
- [ ] `docs/HANDOFF.md` به‌روزرسانی
- [ ] Commit: `docs(specs): update HANDOFF after phase 5A+5B`
- [ ] `git push -u origin phase/5a-voice-entry`
