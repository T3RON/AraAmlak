# Phase 3 — Tasks

## Task 3-0: Create branch + fix urgent bugs
- [ ] `git checkout -b phase/3-matching-dashboard`
- [ ] `settings/base.py` → اضافه کردن `LOGIN_URL`
- [ ] `apps/listings/models.py` → اضافه کردن `get_status_choices` property
- [ ] Commit: `fix(listings,accounts): add LOGIN_URL and get_status_choices`

## Task 3-1: Match model + migration
- [ ] `apps/matching/models.py` — Match (request FK, listing FK, score, agency FK)
- [ ] `apps/matching/migrations/0001_initial.py`
- [ ] `apps/matching/admin.py`
- [ ] Commit: `feat(matching): add Match model and migration`

## Task 3-2: Matching service + Celery task
- [ ] `apps/matching/services.py` — `find_matches(request)` با امتیازبندی
- [ ] `apps/matching/tasks.py` — `run_matching_for_request`
- [ ] `apps/matching/signals.py` — post_save signal
- [ ] `apps/matching/apps.py` — `ready()` hook
- [ ] Commit: `feat(matching): add matching service, task, and signals`

## Task 3-3: Matching views + URLs + templates
- [ ] `apps/matching/views.py` — `RequestMatchListView`
- [ ] `apps/matching/urls.py`
- [ ] `ara_amlak/urls.py` → include matching URLs
- [ ] `templates/matching/match_list.html` — کارت‌های match
- [ ] لینک از `crm/detail.html` به match list
- [ ] Commit: `feat(matching): add match list views, urls, templates`

## Task 3-4: Real dashboard
- [ ] `apps/dashboard/views.py` — context با آمار واقعی (listing/request/match counts)
- [ ] `templates/dashboard/home.html` — کارت‌های آماری با اعداد واقعی
- [ ] Commit: `feat(dashboard): real stats cards with agency-scoped counts`

## Task 3-5: Tests
- [ ] `tests/test_matching_nogis.py` — matching service, امتیازبندی، ایزولاسیون
- [ ] `tests/test_matching_isolation.py` — PostGIS-only tenant isolation
- [ ] Commit: `test(matching): add no-GIS and tenant isolation tests`

## Task 3-6: Cleanup + docs
- [ ] `python -m ruff check .` → clean
- [ ] `python -m pytest --ds=ara_amlak.settings.testing_nogis ... -v` → all green
- [ ] `docs/HANDOFF.md` → update
- [ ] `specs/phase-3/tasks.md` → mark all done
- [ ] Commit: `docs(specs): update HANDOFF and phase-3 tasks`
- [ ] `git push -u origin phase/3-matching-dashboard`
