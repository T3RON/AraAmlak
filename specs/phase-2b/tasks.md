# Phase 2B — Tasks

- [x] T1 — spec files (specify/plan/tasks)
- [x] T2 — Models: Interaction, Visit, Task, Notification + CheckConstraint + indexes
- [x] T3 — Migration `crm/0004_interaction_notification_task_visit`
- [x] T4 — Admin registration
- [x] T5 — Service layer (add_interaction, schedule_visit, complete_visit, create_task, complete_task, get_timeline, notify)
- [x] T6 — Celery beat task `send_due_task_reminders` + beat schedule entry (every 30 min)
- [x] T7 — Views + templates: timeline page+quick-add, visit create/complete, task list/toggle, my-day page, notifications list + mark-read
- [x] T8 — URL wiring: mount moved from `/crm/requests/` to `/crm/` (URL names unchanged)
- [x] T9 — Tests `tests/test_2b_timeline_visit_tasks.py` (26 tests)
- [x] T10 — Full suite (218 passed) + ruff clean + makemigrations --check clean
- [x] T11 — Listing detail now shows visits + timeline; notification badge in base.html
- [ ] T12 — HANDOFF.md update, commit, push, PR
