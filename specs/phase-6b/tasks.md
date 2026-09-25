# Phase 6B — Tasks

## Task 6B-0: شاخه + اسپک
- [x] `git checkout -b phase/6b-poster-font` (از phase/5c-llm-draft)
- [x] `specs/phase-6b/plan.md`
- [x] Commit: `docs(specs): record phase 6B poster font plan`

## Task 6B-1: embed فونت
- [x] `apps/rendering/services.py` — _font_data_uris + context
- [x] `templates/rendering/poster.html` — @font-face شرطی
- [x] Commit: `feat(rendering): embed Vazirmatn fonts in poster html`

## Task 6B-2: تست + Docs
- [x] `tests/test_6a_rendering.py` — دو تست فونت
- [x] Commit: `test(rendering): cover embedded poster fonts`
- [x] `ruff` + pytest کامل + `docs/HANDOFF.md` + push
