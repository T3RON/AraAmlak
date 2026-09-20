# Phase 3 — Plan

## معماری

```
apps/matching/
├── models.py        ← Match(request, listing, score, agency)
├── services.py      ← find_matches(request) → list[Match]
├── tasks.py         ← run_matching_for_request(request_id)
├── signals.py       ← post_save Request → dispatch task
├── apps.py          ← ready() hook for signals
├── admin.py
├── urls.py          ← /matching/requests/<pk>/matches/
├── views.py         ← MatchListView (per request)
└── migrations/
    └── 0001_initial.py

templates/matching/
└── match_list.html  ← کارت‌های فایل match‌شده با badge امتیاز
```

## لایه سرویس (matching/services.py)

```python
def find_matches(request: Request) -> list[Match]:
    """
    1. Hard-filter: agency, deal_type, status=active
    2. Score each candidate listing
    3. Bulk upsert Match records (score > 0)
    4. Return ordered list
    """
```

## امتیازبندی

| معیار | امتیاز |
|-------|--------|
| city یکسان | +۳۰ |
| property_type در property_types | +۲۵ |
| area در بازه | +۲۰ |
| قیمت در بودجه | +۱۵ |
| اتاق در بازه | +۱۰ |
| حداکثر ممکن | ۱۰۰ |

## Signal flow

```
Request.save() → post_save signal → run_matching_for_request.delay(request.pk)
                                    ↓ (Celery worker / در dev: eager)
                                 find_matches(request)
                                    ↓
                               Match.objects.bulk_create / update_or_create
```

## Dashboard

`dashboard/views.py` — context:
```python
{
  "active_listings": Listing.objects.filter(agency=agency, status='active').count(),
  "new_requests": Request.objects.filter(agency=agency, status='new').count(),
  "matches_today": Match.objects.filter(agency=agency, created_at__date=today).count(),
  "total_listings": Listing.objects.filter(agency=agency).count(),
  "total_requests": Request.objects.filter(agency=agency).count(),
}
```

## وابستگی‌ها
- `matching` depends on: `listings`, `crm`, `agencies`
- هیچ circular dep جدیدی نیست
- Celery با `CELERY_TASK_ALWAYS_EAGER=True` در تست (local dev)

## Migrations
- `matching/0001_initial.py` — Match model
- هیچ تغییر schema به listings یا crm نمی‌دهد (read-only FK)
