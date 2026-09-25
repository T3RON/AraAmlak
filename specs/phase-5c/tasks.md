# Phase 5C — Tasks

## Task 5C-0: شاخه + اسپک
- [ ] `git checkout -b phase/5c-llm-draft` (از phase/7a-portal-publishing)
- [ ] `specs/phase-5c/plan.md`
- [ ] Commit: `docs(specs): record phase 5C llm draft plan`

## Task 5C-1: Providerها + سرویس
- [ ] `apps/ai/providers/draft_base.py` — DraftProvider ABC
- [ ] `apps/ai/providers/regex_draft.py` — RegexPersianDraftProvider
- [ ] `apps/ai/providers/gemini_draft.py` — GeminiDraftProvider (schema + نرمال‌سازی)
- [ ] `apps/ai/services.py` — get_draft_provider_for_agency + extract_draft(provider)
- [ ] Commit: `feat(ai): add draft provider abstraction with Gemini structured output`

## Task 5C-2: Celery task + views
- [ ] `apps/ai/tasks.py` — extract_draft_task
- [ ] `apps/ai/views.py` — draft_generate مسیر دوگانه + draft_status
- [ ] `templates/ai/partials/draft_pending.html`
- [ ] Commit: `feat(ai): add async llm draft extraction flow`

## Task 5C-3: تست‌ها
- [ ] `tests/test_5c_llm_draft.py`
- [ ] Commit: `test(ai): add llm draft extraction tests`

## Task 5C-4: Cleanup + Docs
- [ ] `ruff check .` → پاک؛ pytest کامل → سبز
- [ ] `docs/HANDOFF.md` به‌روزرسانی
- [ ] Commit: `docs(specs): update HANDOFF after phase 5C`
- [ ] `git push -u origin phase/5c-llm-draft`
