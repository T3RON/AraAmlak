# Phase 7A — Tasks

## Task 7-0: شاخه + اسپک
- [ ] `git checkout -b phase/7a-portal-publishing` (از phase/6a-poster-render)
- [ ] `specs/phase-7/plan.md`
- [ ] Commit: `docs(specs): record phase 7 divar publishing plan`

## Task 7-1: آداپتور واقعی دیوار
- [ ] `apps/publishing/adapters.py` — DivarAdapter + ثبت در ADAPTER_MAP
- [ ] Commit: `feat(publishing): add real Divar Kenar adapter`

## Task 7-2: تست‌های mocked-HTTP
- [ ] `tests/test_7a_divar_publishing.py`
- [ ] Commit: `test(publishing): add Divar adapter tests with mocked HTTP`

## Task 7-3: Cleanup + Docs
- [ ] `ruff check .` → پاک؛ pytest کامل → سبز
- [ ] `docs/HANDOFF.md` به‌روزرسانی
- [ ] Commit: `docs(specs): update HANDOFF after phase 7A`
- [ ] `git push -u origin phase/7a-portal-publishing`
