# Phase 7A — Tasks

## Task 7-0: شاخه + اسپک
- [x] `git checkout -b phase/7a-portal-publishing` (از phase/6a-poster-render)
- [x] `specs/phase-7/plan.md`
- [x] Commit: `docs(specs): record phase 7 divar publishing plan`

## Task 7-1: آداپتور واقعی دیوار
- [x] `apps/publishing/adapters.py` — DivarAdapter + ثبت در ADAPTER_MAP
- [x] Commit: `feat(publishing): add real Divar Kenar adapter`

## Task 7-2: تست‌های mocked-HTTP
- [x] `tests/test_7a_divar_publishing.py`
- [x] Commit: `test(publishing): add Divar adapter tests with mocked HTTP`

## Task 7-3: Cleanup + Docs
- [x] `ruff check .` → پاک؛ pytest کامل → سبز
- [x] `docs/HANDOFF.md` به‌روزرسانی
- [x] Commit: `docs(specs): update HANDOFF after phase 7A`
- [x] `git push -u origin phase/7a-portal-publishing`
