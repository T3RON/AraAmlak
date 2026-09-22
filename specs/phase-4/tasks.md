# Phase 4 — Tasks

## Task 4-0: ایجاد شاخه
- [x] `git checkout -b phase/4-publishing`

## Task 4-1: مدل‌ها + migration
- [x] `apps/publishing/models.py` — PortalConfig, PublishJob
- [x] `apps/publishing/migrations/0001_initial.py`
- [x] Commit: `feat(publishing): add PortalConfig and PublishJob models`

## Task 4-2: Adapter + Service + Celery task
- [x] `apps/publishing/adapters.py` — BasePortalAdapter, DummyAdapter, ADAPTER_MAP
- [x] `apps/publishing/services.py` — `publish_listing(listing_id, config_id)`
- [x] `apps/publishing/tasks.py` — `publish_listing_task` Celery task
- [x] Commit: `feat(publishing): add adapter pattern, service, and celery task`

## Task 4-3: Admin
- [x] `apps/publishing/admin.py` — PortalConfigAdmin, PublishJobAdmin
- [x] Commit: `feat(publishing): add admin for PortalConfig and PublishJob`

## Task 4-4: Views + URLs + Templates
- [x] `apps/publishing/views.py` — ListingPublishJobListView + PublishCreateView
- [x] `apps/publishing/urls.py` — `/publishing/listings/<pk>/jobs/`
- [x] `ara_amlak/urls.py` → include publishing URLs
- [x] `templates/publishing/publish_job_list.html`
- [x] لینک از `templates/listings/detail.html` به publish job list
- [x] Commit: `feat(publishing): add publish job list view, urls, template`

## Task 4-5: Dashboard
- [x] `apps/dashboard/views.py` — کارت published_today
- [x] `templates/dashboard/home.html` — کارت ششم
- [x] Commit: `feat(dashboard): add published_today stat card`

## Task 4-6: Tests
- [x] `tests/test_publishing_nogis.py` — adapter, service, isolation (12 تست)
- [x] Commit: `test(publishing): add no-GIS publishing tests`

## Task 4-7: Cleanup + Docs
- [x] `python -m ruff check .` → clean
- [x] `python -m pytest --ds=ara_amlak.settings.testing_nogis ... -v` → 72 passed
- [x] `docs/HANDOFF.md` → update
- [x] `specs/phase-4/tasks.md` → mark all done
- [x] Commit: `docs(specs): update HANDOFF for phase 4`
- [ ] `git push -u origin phase/4-publishing`
