# Clarify — Phase 1

## Ambiguities Resolved from the Project Constitution

| # | Question | Resolution (from constitution or standard practice) |
|---|----------|-----------------------------------------------------|
| 1 | Which SMS provider for OTP? | **Stub only** in phase 1. Real integration in a later phase (constitution §8 requires reading official docs first; no provider specified yet). |
| 2 | JWT or session for web views? | Session for template views (HTMX), JWT for DRF API endpoints — standard Django pattern. |
| 3 | `django-tailwind` vs standalone Tailwind CLI? | Standalone Tailwind CLI via Docker (no Node in production image); `django-tailwind` adds Node dependency unnecessarily. |
| 4 | Encrypted fields: which library? | `cryptography` (Fernet) directly — avoids abandoned `django-fernet-fields`; wrap as a custom `EncryptedCharField`. |
| 5 | PostGIS: how to enable in Docker? | `postgis/postgis:16-3.4` Docker image; run `CREATE EXTENSION IF NOT EXISTS postgis;` in a data migration. |
| 6 | `pg_trgm` and `unaccent`: when to enable? | In the same initial data migration as PostGIS. |
| 7 | Jalali library? | `django-jalali` (most maintained). Store Gregorian in DB, display Jalali in templates via template tags. |
| 8 | Apple-HIG dark mode: CSS variable strategy? | Tailwind `darkMode: 'class'`; toggle via Alpine.js; persist in `localStorage`. |
| 9 | Superadmin vs agency owner: same `CustomUser`? | Yes, `role` field discriminates. Superadmin has `agency=None` and `is_staff=True`. |
| 10 | OTP code storage: DB or cache? | Redis (cache), with TTL = 2 min, max 5 attempts. Never logged. |

## Open Items (Not in this Phase)
- Which Telegram/Bale/Rubika channel(s) to publish listings to — deferred to publishing phase.
- Gemini API version and model name — deferred to ai phase (must read official docs then).
- Accounting currency rounding rules — deferred to accounting phase.
