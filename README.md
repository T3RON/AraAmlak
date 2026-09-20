# آرا املاک — Ara Amlak

[![CI](https://github.com/T3RON/AraAmlak/actions/workflows/ci.yml/badge.svg)](https://github.com/T3RON/AraAmlak/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.2_LTS-green)](https://djangoproject.com)

پلتفرم مدیریت چندآژانسی برای مشاوران املاک ایران.

هر «آژانس» یک tenant مجزاست. «فایل» = ملک ثبت‌شده برای فروش یا اجاره؛ «درخواست» = نیازمندی مشتری.

---

## ویژگی‌ها

- 🏢 **چندآژانسی (Multi-tenant):** هر آژانس داده‌های کاملاً مجزا دارد
- 📱 **ورود با OTP:** احراز هویت مبتنی بر شماره موبایل (SMS)
- 🗺️ **PostGIS:** جستجوی جغرافیایی و نمایش روی نقشه
- 🇮🇷 **فارسی کامل:** RTL، تقویم جلالی، ارقام فارسی، فونت وزیرمتن
- ⚡ **ASGI:** Django Channels + Daphne برای WebSocket
- 🔄 **Celery:** پردازش غیرهمزمان (SMS، AI، انتشار، رندر)

---

## راه‌اندازی سریع

### پیش‌نیازها
- Docker Desktop
- Git

### مراحل

```bash
# ۱. کلون پروژه
git clone https://github.com/T3RON/AraAmlak.git
cd AraAmlak

# ۲. کپی متغیرهای محیطی
cp .env.example .env
# فایل .env را ویرایش کنید و مقادیر واقعی بگذارید

# ۳. راه‌اندازی همه سرویس‌ها
make up
```

در مرورگر: **http://localhost:8000**  
پنل ادمین: **http://localhost:8000/admin/**  
بررسی سلامت: **http://localhost:8000/health/**  
Swagger API: **http://localhost:8000/api/docs/**

---

## دستورهای Makefile

| دستور | توضیح |
|-------|-------|
| `make up` | راه‌اندازی همه سرویس‌ها (build + start) |
| `make down` | توقف و حذف کانتینرها |
| `make test` | اجرای تست‌ها |
| `make lint` | بررسی کد با ruff |
| `make migrate` | اجرای migration‌ها |
| `make shell` | Django shell |
| `make seed` | بارگذاری داده اولیه |
| `make logs` | نمایش لاگ سرویس web |

---

## اجرای تست

```bash
# داخل Docker (توصیه‌شده)
make test

# محلی (بدون Docker، برای تست‌های بدون GIS)
pip install -r requirements/dev.txt
DJANGO_SETTINGS_MODULE=ara_amlak.settings.testing_nogis pytest tests/test_core_currency.py tests/test_encrypted_field.py tests/test_otp.py -v
```

---

## ساختار پروژه

```
ara_amlak/          ← پکیج اصلی Django
├── settings/
│   ├── base.py     ← تنظیمات پایه
│   ├── development.py
│   ├── production.py
│   └── testing.py
├── celery.py
├── urls.py
└── asgi.py

apps/
├── core/           ← مدل‌های پایه، utilities، middleware، /health
├── accounts/       ← CustomUser، OTP، احراز هویت
├── agencies/       ← Agency، Branch، AgencyMember
├── listings/       ← فایل‌های ملکی (فاز ۲)
├── crm/            ← درخواست‌ها (فاز ۲)
└── ...             ← ۱۲ اپ در مجموع

templates/          ← قالب‌های HTML (RTL، فارسی)
static/             ← CSS، JS، فونت وزیرمتن
specs/              ← Spec Kit: constitution + زیرفازها
docker/             ← Dockerfile‌ها
```

---

## متغیرهای محیطی

فایل `.env.example` را ببینید. مهم‌ترین‌ها:

| متغیر | توضیح |
|-------|-------|
| `SECRET_KEY` | کلید محرمانه Django |
| `DATABASE_URL` | آدرس PostgreSQL (`postgis://...`) |
| `REDIS_URL` | آدرس Redis |
| `FIELD_ENCRYPTION_KEY` | کلید Fernet برای رمزنگاری فیلدها |

---

## قرارداد کامیت

قالب اجباری: `<type>(<scope>): <subject>`

```
feat(listings): add property search with PostGIS radius filter

Phase: 2
```

جزئیات در [`CONTRIBUTING.md`](CONTRIBUTING.md).

برای نصب hooks:
```bash
pip install pre-commit gitlint
pre-commit install --hook-type commit-msg
pre-commit install
git config commit.template .gitmessage
```

---

## مشارکت

راهنمای کامل در [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## لایسنس

MIT © آرا املاک
