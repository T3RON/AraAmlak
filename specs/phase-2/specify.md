# Phase 2 — Specify: Listings & CRM

## Scope
Implement the `listings` and `crm` apps — the core business models for Ara Amlak.

---

## listings app — «فایل ملک»

### Domain
A **Listing** (فایل) is a property registered by an agent for sale, rent, or mortgage-rent.
Each listing belongs to exactly one agency (tenant-scoped).

### Field Groups

#### Identity
- `code` — auto-generated unique code per agency, e.g. «A-۱۰۰۱»
- `title` — optional free-text title (for display)

#### Property Type
- `property_type`: apartment | villa | commercial | land | office | warehouse | other
- `deal_type`: sale | rent | mortgage_rent | pre_sale

#### Location
- `province` — free text (استان)
- `city` — free text (شهر)  
- `district` — free text (منطقه/محله)
- `address` — full address text
- `location` — PostGIS `PointField` (optional, geography=True)

#### Physical Attributes
- `area` — PositiveIntegerField (متراژ, m²)
- `rooms` — PositiveSmallIntegerField (تعداد اتاق, 0=بدون اتاق)
- `floor` — IntegerField nullable (طبقه)
- `total_floors` — PositiveSmallIntegerField nullable
- `build_year` — PositiveSmallIntegerField nullable (سال ساخت, Gregorian stored)
- `parking` — BooleanField
- `elevator` — BooleanField
- `storage` — BooleanField
- `direction` — choices: north | south | east | west | north_east | north_west | south_east | south_west | '' (جهت)

#### Pricing (BigIntegerField, Tomans)
- `sale_price` — nullable (قیمت فروش)
- `mortgage_amount` — nullable (رهن)
- `rent_amount` — nullable (اجاره ماهانه)
- `price_negotiable` — BooleanField default True

#### Status & Workflow
- `status`: active | reserved | sold | expired | draft — default active
- `owner_name` — CharField (نام مالک, internal, not public)
- `owner_phone` — CharField (شماره مالک, internal, encrypted)
- `assigned_to` — FK to CustomUser nullable (مشاور مسئول)
- `branch` — FK to Branch nullable

#### Media
- `ListingImage` — separate model: listing FK + image + order + is_cover

#### Timestamps
- inherited from `AgencyOwned` → `TimeStampedModel`: `created_at`, `updated_at`
- `published_at` — DateTimeField nullable (زمان انتشار)
- `expires_at` — DateTimeField nullable (تاریخ انقضا)

---

## crm app — «درخواست / سرنخ»

### Domain
A **Request** (درخواست) is a buyer/renter need registered by an agent on behalf of a client.
Each request belongs to exactly one agency (tenant-scoped).

### Field Groups

#### Client
- `client_name` — CharField
- `client_phone` — CharField (encrypted)
- `source`: walk_in | referral | portal | social | direct | other (منبع مراجعه)

#### Need Specification
- `deal_type`: sale | rent | mortgage_rent | pre_sale
- `property_types` — ManyToMany to a `PropertyTypeChoice` or simple ArrayField of choices
  → Use `CharField` with comma-separated choices for simplicity (no ArrayField dep)
  → Actually use a JSONField storing list of choices
- `min_area` / `max_area` — nullable PositiveIntegerField
- `min_rooms` / `max_rooms` — nullable PositiveSmallIntegerField
- `city` / `district` — free text
- `min_budget` / `max_budget` — nullable BigIntegerField (Tomans)
- `notes` — TextField blank

#### Status
- `status`: new | in_progress | matched | closed | cancelled — default new
- `assigned_to` — FK to CustomUser nullable
- `priority`: low | normal | high | urgent — default normal

#### Timestamps
- from `AgencyOwned`: `created_at`, `updated_at`
- `contacted_at` — DateTimeField nullable (آخرین تماس)
- `closed_at` — DateTimeField nullable

---

## Out of Scope for Phase 2
- Matching engine (Phase 3)
- Publishing to portals (Phase 4)
- Media upload (file upload endpoint — Phase 2.5)
- Full-featured UI beyond list + detail + create form
