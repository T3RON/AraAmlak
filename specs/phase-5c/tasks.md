# Phase 5C — Tasks

## Task 5C-0: شاخه + اسپک
- [x] `git checkout -b phase/5c-llm-draft` (از phase/7a-portal-publishing)
- [x] `specs/phase-5c/plan.md`
- [x] Commit: `docs(specs): record phase 5C llm draft plan`

## Task 5C-1: Providerها + سرویس
- [x] `apps/ai/providers/draft_base.py` — DraftProvider ABC
- [x] `apps/ai/providers/regex_draft.py` — RegexPersianDraftProvider
- [x] `apps/ai/providers/gemini_draft.py` — GeminiDraftProvider (schema + نرمال‌سازی)
- [x] `apps/ai/services.py` — get_draft_provider_for_agency + extract_draft(provider)
- [x] Commit: `feat(ai): add draft provider abstraction with Gemini structured output`

## Task 5C-2: Celery task + views
- [x] `apps/ai/tasks.py` — extract_draft_task
- [x] `apps/ai/views.py` — draft_generate مسیر دوگانه + draft_status
- [x] `templates/ai/partials/draft_pending.html`
- [x] Commit: `feat(ai): add async llm draft extraction flow`

## Task 5C-3: تست‌ها
- [x] `tests/test_5c_llm_draft.py`
- [x] Commit: `test(ai): add llm draft extraction tests`

## Task 5C-4: Cleanup + Docs
- [x] `ruff check .` → پاک؛ pytest کامل → سبز
- [x] `docs/HANDOFF.md` به‌روزرسانی
- [x] Commit: `docs(specs): update HANDOFF after phase 5C`
- [x] `git push -u origin phase/5c-llm-draft`
