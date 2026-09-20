# Phase 2 — Plan

## Architecture Decisions

### 1. Tenant Isolation
Both `Listing` and `Request` inherit `AgencyOwned` → automatic `agency` FK + `AgencyManager`.
`ListingImage` has `listing` FK only (inherits tenant via listing; no direct agency FK needed).

### 2. Encrypted Fields
`owner_phone` and `client_phone` use `EncryptedCharField` from `apps.core.fields`.

### 3. GIS Field Guard
`location = PointField(...)` is wrapped with `try/except ImportError` + settings check identical
to how `agencies` does it, so the model imports cleanly without GDAL on Windows.

### 4. Code Generation
`Listing.code` auto-generated via `pre_save` signal or `save()` override:
Format: `<agency_slug_prefix>-<4-digit sequence>` — stored as CharField, unique per agency.
Sequence via `all_objects.filter(agency=...).count() + 1`. Simple, no race condition in MVP.

### 5. Service Layer
- `listings/services.py`: `create_listing()`, `update_listing()`, `expire_listings()` (Celery task)
- `crm/services.py`: `create_request()`, `update_request()`, `close_request()`

### 6. Views (thin)
- ListView + DetailView + CreateView + UpdateView — class-based, mixin for agency scope
- HTMX: inline status update, delete confirmation modal, image reorder
- URL patterns: `/listings/`, `/listings/<pk>/`, `/listings/add/`, `/listings/<pk>/edit/`
- URL patterns: `/crm/requests/`, `/crm/requests/add/`, etc.

### 7. Migrations
- `listings/0001_initial.py` — Listing + ListingImage tables
- `crm/0001_initial.py` — Request table
- Both have PostGIS guard identical to `core/0001_extensions.py`

### 8. Testing Strategy
- `tests/test_listings_isolation.py` — tenant isolation (PostGIS/Docker)
- `tests/test_listings_nogis.py` — model logic, services, currency (no-GIS safe)
- `tests/test_crm_isolation.py` — tenant isolation
- `tests/test_crm_nogis.py` — model logic, services

## File Structure

```
apps/
  listings/
    models.py         ← Listing, ListingImage, enums
    services.py       ← create_listing, update_listing, expire_listings
    views.py          ← ListingListView, ListingDetailView, ListingCreateView, ListingUpdateView
    urls.py
    admin.py
    tasks.py          ← expire_listings Celery task
    migrations/
      0001_initial.py
  crm/
    models.py         ← Request, enums
    services.py       ← create_request, update_request
    views.py          ← RequestListView, RequestCreateView, RequestUpdateView
    urls.py
    admin.py
    migrations/
      0001_initial.py
templates/
  listings/
    list.html
    detail.html
    form.html         ← shared create/edit
  crm/
    list.html
    form.html
tests/
  test_listings_nogis.py
  test_listings_isolation.py
  test_crm_nogis.py
  test_crm_isolation.py
```
