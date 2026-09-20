# Phase 4 — Tasks

## Task 4-0: ایجاد شاخه
- [x] `git checkout -b phase/4-publishing`

## Task 4-1: مدل‌ها + migration
- [ ] `apps/publishing/models.py` — PortalConfig, PublishJob
- [ ] `apps/publishing/migrations/0001_initial.py`
- [ ] Commit: `feat(publishing): add PortalConfig and PublishJob models`

## Task 4-2: Adapter + Service + Celery task
- [ ] `apps/publishing/adapters.py` — BasePortalAdapter, DummyAdapter, ADAPTER_MAP
- [ ] `apps/publishing/services.py` — `publish_listing(listing_id, config_id)`
- [ ] `apps/publishing/tasks.py` — `publish_listing_task` Celery task
- [ ] Commit: `feat(publishing): add adapter pattern, service, and celery task`

## Task 4-3: Admin
- [ ] `apps/publishing/admin.py` — PortalConfigAdmin, PublishJobAdmin
- [ ] Commit: `feat(publishing): add admin for PortalConfig and PublishJob`

## Task 4-4: Views + URLs + Templates
- [ ] `apps/publishing/views.py` — ListingPublishJobListView + PublishCreateView
- [ ] `apps/publishing/urls.py` — `/publishing/listings/<pk>/jobs/`
- [ ] `ara_amlak/urls.py` → include publishing URLs
- [ ] `templates/publishing/publish_job_list.html`
- [ ] لینک از `templates/listings/listing_detail.html` (یا crm)
- [ ] Commit: `feat(publishing): add publish job list view, urls, template`

## Task 4-5: Dashboard
- [ ] `apps/dashboard/views.py` — کارت published_today
- [ ] `templates/dashboard/home.html` — کارت ششم
- [ ] Commit: `feat(dashboard): add published_today stat card`

## Task 4-6: Tests
- [ ] `tests/test_publishing_nogis.py` — adapter, service, isolation (حداقل ۱۰ تست)
- [ ] Commit: `test(publishing): add no-GIS publishing tests`

## Task 4-7: Cleanup + Docs
- [ ] `python -m ruff check .` → clean
- [ ] `python -m pytest --ds=ara_amlak.settings.testing_nogis ... -v` → all green
- [ ] `docs/HANDOFF.md` → update
- [ ] `specs/phase-4/tasks.md` → mark all done
- [ ] Commit: `docs(specs): update HANDOFF for phase 4`
- [ ] `git push -u origin phase/4-publishing`
