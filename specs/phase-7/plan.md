# Phase 7A — Real Portal Publishing Plan (Divar / کنار)

## هدف

انتشار **واقعی** فایل ملک به **دیوار** از طریق پلتفرم رسمی **کنار (Kenar)**.
شیپور API عمومی مستند ندارد و در این فاز آداپتور ندارد (فقط دیوار).

## مستندات رسمی (خوانده‌شده ۲۰۲۶-۰۹ — قانون §10)

- مستندات: https://divar-ir.github.io/kenar-docs
- SDK رسمی: https://github.com/divar-ir/kenar-sdk-python (Postman: postman.com/kenardivar)

| مرحله | Endpoint (base: `https://open-api.divar.ir`) | توضیح |
|-------|----------------------------------------------|-------|
| ۱. آدرس آپلود | `GET /v2/open-platform/post/upload-urls` | پاسخ: `{"image": {"http_method", "url"}, "video": ...}` |
| ۲. آپلود عکس | همان `url` با `http_method` پاسخ (POST/PUT) + هدر X-API-Key | بدنه = باینری عکس؛ URL خودش شناسه عکس است |
| ۳. ثبت آگهی | `POST /experimental/open-platform/posts/new-v2` | پاسخ: `{"post_token": "..."}` |

**Body ثبت:**
```json
{
  "general_data": {
    "title", "description", "city", "category_slug",
    "chat_enabled", "hide_phone", "images": [],
    "location_type": "LOCATION_TYPE_EMPTY | LOCATION_TYPE_EXACT | LOCATION_TYPE_APPROXIMATE",
    "district": "(اختیاری)"
  },
  "category_fields": { }   ← فیلدهای اختصاصی دسته (schema هر دسته)
}
```

**احراز:** هدر `X-API-Key` — ذخیره در `PortalConfig.credentials` (رمزنگاری‌شده).

**schema فیلدهای دسته:** https://kenar.divar.dev/openapi-doc/assets-get-submit-schema/
چون schema وابسته به دسته است و کلیدها را نباید حدس زد، `category_fields` از
`extra_config` آژانس خوانده می‌شود و آداپتور مقادیر فیلدهای لیستینگ را با
`field_map` (کلید پورتال → فیلد لیستینگ) جای‌گذاری می‌کند.

## معماری

تغییر در الگوی موجود فاز 4 — افزونه، نه بازنویسی:

```
apps/publishing/adapters.py
└── DivarAdapter (جدید)      ← ADAPTER_MAP["divar"]
    ├── publish(listing, config) → {"external_id": post_token}
    ├── _build_title/_build_description  (ترکیب فارسی از لیستینگ)
    ├── _upload_images  (upload-urls → PUT باینری؛ حداکثر ۳ عکس، بدون عکس هم ادامه)
    └── _submit         (posts/new-v2 → post_token)
```

- `get_adapter(portal)` دست‌نخورده — آداپتور credentials را در `publish()`
  از `config.credentials` می‌خواند.
- سرویس/تسک/views فاز 4 بدون تغییر کار می‌کنند (job state machine موجود).
- Sheypoor: آداپتور ثبت نمی‌شود — API عمومی مستند ندارد (توقف آگاهانه).

## extra_config مورد انتظار (دیوار)

```json
{
  "category_slug": "apartment-sell",
  "category_fields": {"price": "{{sale_price}}", "meter": "{{area}}"},
  "chat_enabled": true,
  "hide_phone": false,
  "location_type": "LOCATION_TYPE_APPROXIMATE",
  "max_images": 3
}
```

`category_fields` مقادیر `{{listing_field}}` را از خود لیستینگ پر می‌کند
(sale_price / rent_amount / mortgage_amount / area / rooms / floor / build_year).

## خطاها

- credentials خالی / category_slug غایب → `PublishError` (job=failed)
- HTTP غیر ۲xx یا پاسخ بدون `post_token` → `PublishError` با پیام پاسخ
- آپلود عکس ناموفق → بدون عکس ادامه (آگهی متن‌محور)، لاگ هشدار

## تست‌ها (mocked HTTP — هیچ تماس واقعی)

- payload صحیح (title/description/city/category_slug/location_type/هدر X-API-Key)
- آپلود عکس: GET upload-urls → PUT باینری → images شامل URL
- خطاها: ۴xx/۵xx، پاسخ بدون post_token، config ناقص
- سرویس end-to-end: publish_listing با config دیوار → success/failed
