# Phase 4 — Publishing Plan

## هدف

انتشار فایل‌های ملک (Listing) به پورتال‌های آگهی (دیوار، شیپور، ...) از داخل سیستم.

چون API عمومی مستند این پورتال‌ها در دسترس نیست، ما:
1. یک **لایه abstraction** می‌سازیم که هر portal یک adapter مجزا دارد
2. در این فاز فقط یک **stub adapter** (DummyPortal) پیاده می‌کنیم — واقعاً چیزی ارسال نمی‌شود
3. ساختار به شکلی است که بعداً هر portal با یک adapter کلاس واقعی جایگزین شود

## معماری

```
apps/publishing/
├── models.py        ← PortalConfig, PublishJob
├── adapters.py      ← BasePortalAdapter, DummyAdapter
├── services.py      ← publish_listing(listing, portal_config)
├── tasks.py         ← publish_listing_task(listing_id, config_id)
├── signals.py       ← (خالی فعلاً — manual publish)
├── apps.py          ← AppConfig
├── admin.py         ← PortalConfig + PublishJob admin
├── views.py         ← ListingPublishJobListView
├── urls.py          ← /publishing/listings/<pk>/jobs/
└── migrations/
    ├── 0001_initial.py

templates/publishing/
└── publish_job_list.html  ← لیست job‌ها با badge وضعیت
```

## مدل‌ها

### PortalConfig (کانفیگ پورتال برای هر آژانس)
```
agency          FK → Agency
portal          CharField choices (divar, sheypoor, dummy)
is_active       BooleanField
credentials     EncryptedCharField  ← API token/key (رمزنگاری)
extra_config    JSONField           ← تنظیمات اضافه
created_at / updated_at
```

### PublishJob (یک job انتشار)
```
agency          FK → Agency  (denormalized, index)
listing         FK → Listing
portal_config   FK → PortalConfig
status          CharField: pending / running / success / failed
external_id     CharField  ← شناسه آگهی در پورتال
error_message   TextField
published_at    DateTimeField null
retries         PositiveSmallIntegerField default=0
created_at / updated_at
```

## Adapter pattern

```python
class BasePortalAdapter:
    def publish(self, listing, config) -> dict:  # raises PublishError
        raise NotImplementedError

class DummyAdapter(BasePortalAdapter):
    """Always succeeds, returns fake external_id."""
    def publish(self, listing, config) -> dict:
        return {"external_id": f"dummy-{listing.pk}"}

ADAPTER_MAP = {
    "dummy": DummyAdapter,
    # "divar": DivarAdapter,   ← فاز بعدی
}
```

## Service flow

```
publish_listing(listing_id, config_id)
    → job = PublishJob.create(status=pending)
    → adapter = ADAPTER_MAP[config.portal]()
    → result = adapter.publish(listing, config)
    → job.status = success / failed
    → job.save()
```

## Celery task

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def publish_listing_task(self, listing_id, config_id):
    ...
```

## UI

- در صفحه detail هر listing، دکمه «انتشار» + لیست job‌های قبلی
- هر job یک badge وضعیت (pending/running/success/failed)
- لینک از listing detail به `/publishing/listings/<pk>/jobs/`

## تست‌ها

- `tests/test_publishing_nogis.py`:
  - DummyAdapter publish موفق
  - publish_listing service — job ایجاد می‌شود با status=success
  - publish_listing service — وقتی adapter شکست می‌خورد، status=failed
  - PublishJob tenant isolation (آژانس دیگر job دیگری نمی‌بیند)
  - PortalConfig فقط active config‌ها
