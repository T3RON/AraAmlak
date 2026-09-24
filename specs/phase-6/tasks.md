# Phase 6A — Tasks

## Task 6-0: شاخه + اسپک
- [ ] `git checkout -b phase/6a-poster-render` (از phase/5a-voice-entry)
- [ ] `specs/phase-6/plan.md`
- [ ] Commit: `docs(specs): record phase 6 poster render plan`

## Task 6-1: مدل + migration + admin
- [ ] `apps/rendering/models.py` — RenderJob (kind/status ماشین وضعیت)
- [ ] `apps/rendering/migrations/0001_initial.py`
- [ ] `apps/rendering/admin.py`
- [ ] Commit: `feat(rendering): add RenderJob model`

## Task 6-2: engines + سرویس + task
- [ ] `apps/rendering/engines.py` — BaseRenderEngine, PlaywrightRenderEngine, StubRenderEngine
- [ ] `apps/rendering/services.py` — render_poster_html (cover base64)، enqueue/run_render
- [ ] `apps/rendering/tasks.py` — render_poster_task با backoff
- [ ] Commit: `feat(rendering): add render engines, service and celery task`

## Task 6-3: قالب پوستر + views/urls
- [ ] `templates/rendering/poster.html` — self-contained RTL
- [ ] `templates/rendering/render_job_list.html` + `partials/render_job_item.html`
- [ ] `apps/rendering/views.py`, `urls.py` + include در root
- [ ] بخش پوستر در `templates/listings/detail.html`
- [ ] Commit: `feat(rendering): add poster template, job views and urls`

## Task 6-4: تست‌ها
- [ ] `tests/test_6a_rendering.py` — engine ها، pipeline، views، isolation
- [ ] Commit: `test(rendering): add poster render tests`

## Task 6-5: Cleanup + Docs
- [ ] `ruff check .` → پاک؛ pytest کامل → سبز
- [ ] `docs/HANDOFF.md` به‌روزرسانی
- [ ] Commit: `docs(specs): update HANDOFF after phase 6A`
- [ ] `git push -u origin phase/6a-poster-render`
