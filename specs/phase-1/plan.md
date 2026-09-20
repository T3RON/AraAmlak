# Plan — Phase 1

## Architecture Overview

```
ara_amlak/          ← Django project package
├── settings/
│   ├── base.py
│   ├── development.py
│   └── production.py
├── urls.py
├── asgi.py
└── wsgi.py

apps/
├── core/           ← Abstract base models, utilities, middleware
├── accounts/       ← CustomUser, OTP, auth views
├── agencies/       ← Agency, Branch, AgencyMember
├── listings/       ← (stub)
├── crm/            ← (stub)
├── matching/       ← (stub)
├── messaging/      ← (stub)
├── ai/             ← (stub)
├── publishing/     ← (stub)
├── rendering/      ← (stub)
├── accounting/     ← (stub)
└── dashboard/      ← (stub)

static/
├── css/            ← Tailwind output
├── js/             ← HTMX, Alpine.js
└── fonts/          ← Vazirmatn

templates/
├── base.html
├── partials/
└── accounts/

docker/
├── Dockerfile
├── Dockerfile.tailwind
└── entrypoint.sh

docker-compose.yml
docker-compose.dev.yml
```

## Component Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Django | 5.2 LTS | Constitution requirement |
| DB | PostgreSQL 16 + PostGIS | Constitution requirement |
| Cache/broker | Redis 7 | Constitution requirement |
| Async | Daphne + Django Channels | Constitution requirement |
| Task queue | Celery 5 + Beat | Constitution requirement |
| Auth | Custom AbstractBaseUser | Phone-based, no username |
| OTP storage | Redis (TTL 120s) | Fast, ephemeral, no DB bloat |
| Secrets encryption | cryptography.Fernet | Maintained, no extra dep |
| Tailwind | Standalone CLI in Docker | No Node in prod image |
| Jalali | django-jalali | Best maintained |
| Linting | ruff | Constitution requirement |
| Testing | pytest-django + factory_boy | Constitution requirement |
| PDF/PNG | Playwright | Constitution requirement |

## Data Flow: OTP Login
```
POST /auth/otp/send/  →  [validate phone]  →  [generate 6-digit code]
  →  [store in Redis: otp:{phone} TTL=120s]
  →  [Celery task: send SMS]
  →  200 OK

POST /auth/otp/verify/  →  [fetch from Redis]
  →  [compare, check attempts]
  →  [delete from Redis]
  →  [create/get User]
  →  [set session / return JWT]
```

## Tenant Isolation Strategy
```python
# Thread-local current agency (set by middleware)
_thread_local = threading.local()

class AgencyManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        agency = getattr(_thread_local, 'current_agency', None)
        if agency is not None:
            return qs.filter(agency=agency)
        return qs
```
Middleware sets `_thread_local.current_agency` from `request.user.agency`.

## Currency Formatting Algorithm
```
۱ میلیارد = 1_000_000_000
۱ میلیون  = 1_000_000
۱ هزار    = 1_000

format_toman(2_700_000_000)  →  "۲ میلیارد و ۷۰۰ میلیون تومان"
format_toman(1_500_000)      →  "۱ میلیون و ۵۰۰ هزار تومان"
format_toman(250_000)        →  "۲۵۰ هزار تومان"
format_toman(5_000)          →  "۵٬۰۰۰ تومان"
```
