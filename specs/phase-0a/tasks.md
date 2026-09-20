# Tasks — Phase 0A

## Task List

- [x] T0A.00  Create branch phase/0a-scaffold, write specs
- [ ] T0A.01  .env.example — complete env vars
- [ ] T0A.02  Makefile with 7 targets
- [ ] T0A.03  /health endpoint (db, redis, celery checks)
- [ ] T0A.04  Homepage view (RTL, Farsi)
- [ ] T0A.05  Fix docker-compose.yml — ensure all 6 services (add celery-beat service if missing)
- [ ] T0A.06  pre-commit config (ruff + gitlint + standard hooks)
- [ ] T0A.07  .gitlint config (type/scope enforcement)
- [ ] T0A.08  .gitmessage commit template
- [ ] T0A.09  CONTRIBUTING.md
- [ ] T0A.10  GitHub Actions CI augment (migration check job + PR commit-msg job)
- [ ] T0A.11  README.md (Farsi, complete)
- [ ] T0A.12  Smoke test update (test /health endpoint)
- [ ] T0A.13  Commit each task, push phase/0a-scaffold, open PR

## Acceptance Criteria
- `docker compose up` starts all 6 services without errors
- `GET /health/` returns `{"status":"ok","db":"ok","redis":"ok","celery":"ok"}`
- `GET /` returns 200 with RTL Farsi homepage
- `pytest` passes all tests
- `ruff check .` returns zero issues
- Committing with a bad message is rejected by pre-commit hook
- CI on GitHub runs green
- PR open on GitHub
