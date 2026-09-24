# Phase 6A — Tasks

## Task 6-0: شاخه + اسپک
- [x] `git checkout -b phase/6a-poster-render` (از phase/5a-voice-entry)
- [x] `specs/phase-6/plan.md`
- [x] Commit: `docs(specs): record phase 6 poster render plan`

## Task 6-1: مدل + migration + admin
- [x] `apps/rendering/models.py` — RenderJob (kind/status ماشین وضعیت)
- [x] `apps/rendering/migrations/0001_initial.py`
- [x] `apps/rendering/admin.py`
- [x] Commit: `feat(rendering): add RenderJob model`

## Task 6-2: engines + سرویس + task
- [x] `apps/rendering/engines.py` — BaseRenderEngine, PlaywrightRenderEngine, StubRenderEngine
- [x] `apps/rendering/services.py` — render_poster_html (cover base64)، enqueue/run_render
- [x] `apps/rendering/tasks.py` — render_poster_task با backoff
- [x] Commit: `feat(rendering): add render engines, service and celery task`

## Task 6-3: قالب پوستر + views/urls
- [x] `templates/rendering/poster.html` — self-contained RTL
- [x] `templates/rendering/render_job_list.html` + `partials/render_job_item.html`
- [x] `apps/rendering/views.py`, `urls.py` + include در root
- [x] بخش پوستر در `templates/listings/detail.html`
- [x] Commit: `feat(rendering): add poster template, job views and urls`

## Task 6-4: تست‌ها
- [x] `tests/test_6a_rendering.py` — engine ها، pipeline، views، isolation
- [x] Commit: `test(rendering): add poster render tests`

## Task 6-5: Cleanup + Docs
- [x] `ruff check .` → پاک؛ pytest کامل → سبز
- [x] `docs/HANDOFF.md` به‌روزرسانی
- [x] Commit: `docs(specs): update HANDOFF after phase 6A`
- [x] `git push -u origin phase/6a-poster-render`
