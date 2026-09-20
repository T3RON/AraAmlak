# Spec — Phase 1: Project Bootstrap & Core Infrastructure

## Scope
Set up the full project skeleton for **Ara Amlak** — a multi-tenant (multi-agency) real-estate web app for Iranian property consultants.

Phase 1 delivers:
1. Docker Compose stack (Django/Daphne, PostgreSQL 16 + PostGIS, Redis, Celery worker, Celery Beat)
2. Django 5.2 project with all 12 app stubs
3. `core` app: base models, managers, middleware, helpers
4. `accounts` app: CustomUser + agency-scoped auth
5. `agencies` app: Agency, Branch, AgencyMember models
6. Tailwind + HTMX + Alpine.js static pipeline
7. Base templates (RTL, Vazirmatn, dark-mode, Apple-HIG aesthetic)
8. Pytest-django + factory_boy setup; CI config
9. ruff linting config
10. Full migrations and tenant-isolation tests for every model

## Functional Requirements

### FR-1  Multi-tenancy
- Every tenant-scoped model has a non-nullable `agency = ForeignKey(Agency)` column.
- A custom default manager (`AgencyManager`) filters `queryset` by `agency` when a thread-local or request context is set.
- `Agency.objects.all()` returns all agencies (superadmin usage).

### FR-2  User & Authentication
- `CustomUser` extends `AbstractBaseUser` + `PermissionsMixin`.
- Fields: `phone` (unique, used as username), `full_name`, `email` (optional), `agency` (FK, nullable for superadmin), `role` (choices: superadmin | owner | agent | viewer), `is_active`, `is_staff`.
- Phone-based OTP login (SMS); password login disabled for normal users.
- JWT tokens (djangorestframework-simplejwt) for API; session for template views.

### FR-3  Agency
- `Agency`: name, slug (unique), logo, phone, address, plan (free|pro|enterprise), is_active.
- `Branch`: agency FK, name, address, location (PostGIS Point), phone.
- `AgencyMember`: user FK + agency FK (unique_together), role, joined_at.

### FR-4  Core Utilities
- `TimeStampedModel` abstract base: created_at, updated_at.
- `AgencyOwned` abstract base: adds `agency` FK + `AgencyManager`.
- Currency helpers: `format_toman(amount: int) -> str` → "۲ میلیارد و ۷۰۰ میلیون تومان".
- Jalali date helpers (using django-jalali).
- Persian numeral conversion utility.
- Encrypted field wrapper (using django-fernet-fields or cryptography directly) for secrets.

### FR-5  UI Base
- Tailwind CSS via `django-tailwind` or standalone CLI (no CDN in production).
- Base template: RTL, `dir="rtl"` on `<html>`, `lang="fa"`, Vazirmatn font (self-hosted), dark-mode class toggle.
- HTMX and Alpine.js loaded from static files.
- Partial template blocks for HTMX swaps.

## Non-Functional Requirements
- TIME_ZONE = Asia/Tehran; USE_TZ = True; all datetimes stored in UTC.
- All monetary values: `BigIntegerField` in Tomans.
- Secrets: never in code or logs; encrypted in DB or env.
- Migrations for every schema change; no data in seeds with real phone/ID numbers.
- Every tenant-scoped model: isolation test (agency A cannot see agency B's data).

## Out of Scope for Phase 1
- listings, crm, matching, messaging, ai, publishing, rendering, accounting, dashboard apps (stubs only).
- SMS provider integration (stub only in accounts).
- Celery tasks beyond infrastructure wiring.
