# Phase 2B — Plan

## Technical Constraints

1. **Models** in `apps/crm/models.py`. All `AgencyOwned` (tenant-scoped via `AgencyManager`).
   `Visit`/`Task`/`Notification`/`Interaction` all inherit `AgencyOwned`.
   - `Interaction` uses explicit nullable FKs + `CheckConstraint` (no ContentType).
   - Indexes: `(agency, occurred_at)`, `(agency, contact, occurred_at)`,
     `(agency, listing, occurred_at)`, `(agency, request, occurred_at)`.
   - Task: index `(assignee, status, due_at)`.
   - Notification: index `(user, is_read, created_at)`.

2. **Migration** `crm/0006_interaction_visit_task_notification` — one migration for all four models.

3. **Admin** registration for all new models (list_display, raw_id FKs, date_hierarchy).

4. **Services** stay in `apps/crm/services.py`; views remain thin (pattern from Phase 2A).
   Agency is resolved from the parent object (listing/request/contact), never trusted from
   request body. `performed_by` = `request.user`.

5. **Tasks (Celery)** in `apps/crm/tasks.py`:
   - `send_due_task_reminders()` — `@periodic_task`/beat schedule entry in
     `config/celery.py` `CELERY_BEAT_SCHEDULE`, crontab every 30 min.
   - In tests `CELERY_TASK_ALWAYS_EAGER=True` so `.delay()` runs inline.

6. **Views**: class-based + HTMX partials. Follow existing template structure under
   `templates/crm/`. Reuse Phase 0B components (card, badge, button) — no new CSS.

7. **Phone masking**: interactions/visits must never leak owner phone to roles that
   cannot see it (secretary role). Views filter fields per role matrix from Phase 0C.

8. **Tests** `tests/test_2b_timeline_visit_tasks.py`:
   - model + CheckConstraint (at-least-one-target) violation raises.
   - service: schedule_visit also creates Interaction; complete_visit sets outcome.
   - tenant isolation: agency A cannot see agency B interactions/visits/tasks/notifications.
   - role matrix: secretary cannot see owner phone in timeline entries.
   - beat task: overdue task → exactly one notification (idempotency via reminder_sent_at).
   - view tests: create visit, complete task via HTMX, my-day page, notification badge.

## Definition of Done
- All tests green (existing 192 + new), `ruff check .` clean,
  `makemigrations --check` reports no changes.
- HANDOFF.md updated.
