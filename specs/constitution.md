# Constitution ظ¤ ╪ت╪▒╪د ╪د┘à┘╪د┌ر

This file is the **authoritative reference** for all architectural and process decisions.
It supersedes any conflicting instruction in individual phase specs.

## 1. Tech Stack (IMMUTABLE ظ¤ do not change without constitution amendment)

| Layer | Technology |
|-------|-----------|
| Framework | Django 5.2 LTS |
| API | DRF (internal API + agent tools only) |
| Frontend | Django Templates + HTMX + Alpine.js + Tailwind CSS |
| Database | PostgreSQL 16 + PostGIS + pg_trgm + unaccent |
| Cache / Broker | Redis 7 |
| Task queue | Celery 5 + Beat |
| WebSocket | Django Channels + Daphne (ASGI) |
| PDF/PNG render | Playwright |
| Testing | pytest-django + factory_boy |
| Linting | ruff |
| Containerisation | Docker Compose |

## 2. Language & Locale

- Default language: **Farsi (fa)**, RTL everywhere
- Jalali calendar in UI (django-jalali); Gregorian stored in DB
- Persian digits in all UI numbers
- `LANGUAGE_CODE = fa`, `TIME_ZONE = Asia/Tehran`, `USE_TZ = True`
- All DB datetimes in **UTC**

## 3. Currency

- Stored as `BigIntegerField` in **Tomans**
- Displayed as: `┬س█▓ ┘à█î┘█î╪د╪▒╪» ┘ê █╖█░█░ ┘à█î┘█î┘ê┘ ╪ز┘ê┘à╪د┘┬╗`

## 4. Multi-tenancy

- Every tenant-scoped model has `agency = ForeignKey(Agency, non-nullable)`
- Default manager (`AgencyManager`) filters by thread-local `current_agency`
- Middleware sets `current_agency` from `request.user.agency`
- Isolation test required for every new tenant-scoped model

## 5. Architecture

- **Service layer**: all business logic in `services.py`; views must be thin
- **Celery**: every external or long-running task (SMS, AI, publish, render, import) ظ¤ no exceptions
- **Secrets**: encrypted in DB (Fernet/EncryptedCharField) or env; never in logs or code
- Secrets in env vars must use `django-environ`; never hardcoded

## 6. Security

- OTP: stored in Redis, TTL 120s, max 5 attempts; never logged
- JWT for DRF API; session for template views
- All secrets via `FIELD_ENCRYPTION_KEY` (Fernet key)
- `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL` always from env

## 7. UI Design (Apple HIG)

- Clear visual hierarchy, generous negative space
- Font: **Vazirmatn** (self-hosted)
- Rounded corners, subtle materials/blur, short animations
- `prefers-reduced-motion` respected
- Dark mode supported (Tailwind `darkMode: 'class'`)
- Mobile-first, WCAG AA accessibility

## 8. Testing

- Every new model: unit test + tenant isolation test
- Every schema change: migration + test
- No real phone numbers or personal data in seeds/tests
- Factories with `factory_boy`, fake data only

## 9. Git Workflow

- Branch: `phase/<number>-<short-desc>` (cut from `main`)
- Commit per completed task; every commit leaves tests green
- Commit message: `<type>(<scope>): <subject>` (Conventional Commits)
  - Types: `feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert`
  - Scopes: `core|accounts|agencies|listings|crm|matching|messaging|ai|publishing|rendering|accounting|dashboard|ui|infra|deps|specs`
  - Subject: English, imperative, lowercase, no period, ظëج72 chars
  - Breaking change: `!` after scope + `BREAKING CHANGE` footer
  - Footer on every commit: `Phase: <phase-number>`
- Push branch to `origin`; PR to `main`
- No direct commits or force-pushes to `main`
- Pre-commit diff check for secrets before every push

## 10. External Service APIs

Per constitution ┬د8 of original spec: always read official docs before implementing any external service (SMS, Telegram, Bale, Rubika, Instagram, Gemini). Never guess endpoints or parameter names from memory.

## 11. Migrations

- Every schema change requires a migration
- Run `makemigrations --check` in CI
- Initial migration activates: `postgis`, `pg_trgm`, `unaccent`
