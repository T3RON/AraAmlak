# Spec — Phase 0A: Full Scaffold & Dev Infrastructure

## Scope
Complete the project skeleton for **Ara Amlak** with a production-ready developer workflow:

1. One-command startup (`make up`) — web, db, redis, celery, celery-beat, channels
2. `/health` endpoint returning JSON status of db, redis, celery
3. Homepage (`/`) with RTL Farsi text and project name
4. Makefile with all targets: `up down test lint migrate shell seed`
5. `.env.example` (complete) + `django-environ` wiring
6. Pre-commit hooks: ruff, gitlint (commit-msg format enforcement)
7. GitHub Actions CI: lint + test + `makemigrations --check` + PR commit-msg validation
8. CONTRIBUTING.md (branch, commit, PR conventions)
9. README in Farsi
10. Spec Kit constitution file

## Functional Requirements

### FR-1  make up
`docker compose up --build` via `make up` starts all 6 services:
- `db` (PostgreSQL 16 + PostGIS)
- `redis`
- `web` (Daphne ASGI)
- `celery` (worker)
- `celery-beat`
- No extra services needed beyond what's in docker-compose.yml

### FR-2  /health
`GET /health/` → `200 OK` JSON:
```json
{
  "status": "ok",
  "db": "ok",
  "redis": "ok",
  "celery": "ok"
}
```
If any check fails, the value is `"error: <reason>"` and HTTP status is `503`.

### FR-3  Homepage
`GET /` → HTML page: RTL, `lang="fa"`, title and h1 = "آرا املاک", brief description.

### FR-4  Commit Format Enforcement
gitlint pre-commit hook rejects commits that:
- Don't follow `<type>(<scope>): <subject>` format
- Have subject > 72 chars
- Use types outside: feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert

### FR-5  CI
GitHub Actions on push + PR:
- Job 1: lint (ruff check)
- Job 2: test (pytest with PostGIS service)
- Job 3: migration check (`manage.py makemigrations --check`)
- Job 4: commit-msg validation for PR commits

## Constitution (project-wide invariants)

See `specs/constitution.md` — this is the authoritative reference for all phases.

## Out of Scope for Phase 0A
- Any business logic (listings, CRM, matching, etc.)
- Full authentication UI
- Production deployment config
