# Plan ظ¤ Phase 0A

## What needs to be added / fixed relative to existing codebase

The repo already has:
- Django 5.2 project skeleton (`ara_amlak/`)
- 12 app stubs
- docker-compose.yml + Dockerfiles
- requirements/
- ruff config in pyproject.toml
- base templates + Tailwind config
- pytest setup

**Phase 0A adds:**
1. `.env.example` ظ¤ complete with all required vars
2. `Makefile` ظ¤ all 7 targets
3. `/health` view + URL
4. `config/` ظْ renamed to `ara_amlak/settings/` (already exists)
5. pre-commit config with gitlint
6. `.gitmessage` commit template
7. GitHub Actions CI (augment existing `.github/workflows/ci.yml`)
8. PR commit-msg validation workflow
9. CONTRIBUTING.md
10. Revised README (Farsi)
11. Spec Kit constitution + phase-0a spec

## Key Design Decisions

### /health implementation
- Separate `apps/core/health.py` service module
- DB check: `connection.ensure_connection()`
- Redis check: `cache.set/get` with a sentinel key
- Celery check: `app.control.inspect().ping()` with 1s timeout
- View in `apps/core/views.py` ظ¤ returns JSON

### Makefile
```makefile
up:    docker compose up --build
down:  docker compose down
test:  docker compose run --rm web pytest
lint:  docker compose run --rm web ruff check .
migrate: docker compose run --rm web python manage.py migrate
shell:   docker compose run --rm web python manage.py shell
seed:    docker compose run --rm web python manage.py seed
```

### pre-commit hooks order
1. `ruff` (linter + formatter)
2. `gitlint` (commit-msg format)
3. Standard hooks: trailing-whitespace, end-of-file-fixer, check-yaml, check-merge-conflict

### CI Jobs
- `lint`: `ruff check .`
- `test`: `pytest -q --tb=short`
- `migration-check`: `python manage.py makemigrations --check`
- `commitlint`: validate PR commit messages against Conventional Commits
