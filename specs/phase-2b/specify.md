# Phase 2B — Specify: Timeline, Visit, Tasks

## Scope
CRM engagement layer: interaction timeline, property visits (بازدید), tasks/reminders
(وظایف), and in-app notifications (اعلان درون‌برنامه‌ای). Builds on Phase 2A Contact/Request
and Phase 1 Listing.

---

## Domain

### Interaction (تایم‌لاین)
A single engagement touch-point attached to a Contact and (optionally) a Listing and/or Request.
- `kind`: call | sms | note | status_change | visit | other
- `contact` — FK Contact (nullable, but see constraint below)
- `listing` — FK Listing (nullable)
- `request` — FK Request (nullable)
- `summary` — CharField (کوتاه، عنوان رویداد)
- `detail` — TextField blank (یادداشت کامل)
- `performed_by` — FK CustomUser (چه کسی ثبت کرد)
- `occurred_at` — DateTimeField (زمان واقعی رویداد، قابل ویرایش دستی)

**Constraint:** at least one of (`contact`, `listing`, `request`) must be set. Enforced by
`CheckConstraint` (COALESCE count >= 1). ContentType/GenericFK is explicitly forbidden —
explicit nullable FKs only (per roadmap 2B Plan).

### Visit (بازدید)
A scheduled/completed property visit linking a Listing ↔ Contact.
- `listing` — FK Listing (required)
- `contact` — FK Contact (required) — the visitor
- `request` — FK Request (nullable) — if visit originated from a request
- `scheduled_at` — DateTimeField (زمان قرار)
- `completed_at` — DateTimeField nullable (زمان انجام)
- `status`: scheduled | completed | cancelled | no_show
- `outcome`: interested | rejected | thinking | none (نتیجه)
- `note` — TextField blank
- `agent` — FK CustomUser (مشاور همراه)
- Creating a Visit also creates an `Interaction(kind=visit)` (service layer responsibility).

### Task (وظیفه / یادآوری)
A to-do item assigned to a consultant.
- `title` — CharField
- `description` — TextField blank
- `assignee` — FK CustomUser (required)
- `due_at` — DateTimeField (موعد)
- `priority`: low | normal | high — default normal
- `status`: pending | done | cancelled — default pending
- `completed_at` — DateTimeField nullable
- `related_contact` / `related_listing` / `related_request` — all nullable FKs (optional context)
- Overdue = `status=pending AND due_at < now`.

### Notification (اعلان درون‌برنامه‌ای)
Simple badge/list notification (real-time WebSocket arrives in Phase 3C).
- `user` — FK CustomUser (گیرنده)
- `kind`: info | success | warning | error
- `title` — CharField
- `body` — TextField blank
- `link` — CharField blank (URL برای کلیک)
- `is_read` — BooleanField default False
- `read_at` — DateTimeField nullable

---

## Service Layer (apps/crm/services.py additions)
Pure-ish functions, all transactional, all tenant-safe (agency inferred from parent objects):
- `add_interaction(agency, user, kind, contact=None, listing=None, request=None, ...)`
- `schedule_visit(agency, user, listing, contact, scheduled_at, ...) -> Visit`
- `complete_visit(visit, outcome, note) -> Visit` — sets completed_at, status, creates Interaction
- `create_task(agency, user, title, assignee, due_at, ...) -> Task`
- `complete_task(task) -> Task`
- `get_timeline(contact=None, listing=None, request=None) -> QuerySet[Interaction]`
- `notify(user, kind, title, body, link)` — creates Notification

---

## Celery Beat
- `apps/crm/tasks.py::send_due_task_reminders()` — runs every 30 min (beat schedule),
  finds overdue+pending tasks (with a reminder_sent_at guard → one reminder per task),
  creates a Notification for the assignee.

---

## Views & UI
- `InteractionListView` — timeline page with filter by kind and target object.
- Partials injected into Listing detail, Contact detail, Request detail (tabs from 1B).
- Visit create form (from Listing detail), visit complete (HTMX inline).
- Task list + create + complete-toggle (HTMX), page «امروز من» (my day: tasks due today
  + overdue + today's visits).
- Notification badge in header + list + mark-all-read (HTMX).

---

## Out of Scope
- Real-time WebSocket push (Phase 3C).
- Task dependencies/attachments.
- Calendar integration.
