# Tasks — Phase 1

## Task List

- [ ] T1.01  Initialize git, create branch `phase/1-bootstrap`, write specs (this file)
- [ ] T1.02  Write `docker-compose.yml` + `Dockerfile` (app, tailwind, postgres, redis, celery)
- [ ] T1.03  Write `requirements.txt` / `pyproject.toml` with all pinned deps
- [ ] T1.04  Django project scaffold: `ara_amlak/` package, settings (base/dev/prod), urls, asgi, wsgi
- [ ] T1.05  Create all 12 app stubs (`apps/` directory, each with `apps.py`)
- [ ] T1.06  `core` app: `TimeStampedModel`, `AgencyOwned` abstract base, `AgencyManager`, thread-local middleware
- [ ] T1.07  `core` app: currency formatter `format_toman()`, Persian numeral util, Jalali helpers
- [ ] T1.08  `core` app: `EncryptedCharField` (Fernet wrapper)
- [ ] T1.09  `core` app: initial data migration (PostGIS, pg_trgm, unaccent extensions)
- [ ] T1.10  `accounts` app: `CustomUser` model, `UserManager`, migrations
- [ ] T1.11  `accounts` app: OTP service (Redis), SMS stub task (Celery)
- [ ] T1.12  `accounts` app: login/logout views (session), OTP API endpoints (DRF)
- [ ] T1.13  `agencies` app: `Agency`, `Branch`, `AgencyMember` models + migrations
- [ ] T1.14  `agencies` app: admin registrations
- [ ] T1.15  Static pipeline: Tailwind config, download HTMX + Alpine.js + Vazirmatn to static/
- [ ] T1.16  Base templates: `base.html`, RTL, dark-mode toggle, nav skeleton
- [ ] T1.17  `pytest.ini` / `conftest.py`, factory_boy factories for User + Agency
- [ ] T1.18  Tests: tenant isolation for `agencies` + `accounts`
- [ ] T1.19  Tests: currency formatter, Persian numeral, Jalali helpers
- [ ] T1.20  Tests: OTP flow (send, verify, expiry, max-attempts)
- [ ] T1.21  ruff config (`pyproject.toml`), CI config (`.github/workflows/ci.yml`)
- [ ] T1.22  `README.md` with dev setup instructions

## Acceptance Criteria
- `docker compose up` starts all services without errors.
- `pytest` passes all tests (no xfail counted as pass).
- `ruff check .` returns zero issues.
- Django check: `python manage.py check --deploy` (with prod settings) passes.
- Tenant isolation: a user in Agency A cannot retrieve records belonging to Agency B through the ORM manager.
