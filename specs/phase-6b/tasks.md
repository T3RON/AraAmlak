# Phase 6B — Tasks

## Task 6B-0: شاخه + اسپک
- [ ] `git checkout -b phase/6b-poster-font` (از phase/5c-llm-draft)
- [ ] `specs/phase-6b/plan.md`
- [ ] Commit: `docs(specs): record phase 6B poster font plan`

## Task 6B-1: embed فونت
- [ ] `apps/rendering/services.py` — _font_data_uris + context
- [ ] `templates/rendering/poster.html` — @font-face شرطی
- [ ] Commit: `feat(rendering): embed Vazirmatn fonts in poster html`

## Task 6B-2: تست + Docs
- [ ] `tests/test_6a_rendering.py` — دو تست فونت
- [ ] Commit: `test(rendering): cover embedded poster fonts`
- [ ] `ruff` + pytest کامل + `docs/HANDOFF.md` + push
