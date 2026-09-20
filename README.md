# آرا املاک — Ara Amlak

پلتفرم مدیریت چندآژانسی برای مشاوران املاک ایران.

## تکنولوژی‌ها

- **Backend**: Django 5.2 LTS + DRF + Django Channels (Daphne)
- **Database**: PostgreSQL 16 + PostGIS
- **Cache/Queue**: Redis 7 + Celery 5
- **Frontend**: Django Templates + HTMX + Alpine.js + Tailwind CSS
- **Testing**: pytest-django + factory_boy
- **Linting**: ruff

## راه‌اندازی محیط توسعه

### پیش‌نیازها
- Docker Desktop
- Git

### راه‌اندازی

```bash
# کلون پروژه
git clone https://github.com/T3RON/AraAmlak.git
cd AraAmlak

# ساخت و راه‌اندازی سرویس‌ها
docker compose up --build

# در یک ترمینال جداگانه، ساخت سوپرادمین
docker compose exec web python manage.py createsuperuser
```

### آدرس‌های محلی
- وب‌اپ: http://localhost:8000
- پنل ادمین: http://localhost:8000/admin/
- Swagger API: http://localhost:8000/api/docs/

## اجرای تست‌ها

```bash
# داخل Docker
docker compose exec web pytest

# محلی (با محیط مجازی)
pytest
```

## Lint

```bash
ruff check .
ruff check . --fix  # اصلاح خودکار
```

## ساختار پروژه

```
ara_amlak/          ← پکیج Django
apps/
├── core/           ← مدل‌های پایه، utilities، middleware
├── accounts/       ← CustomUser، OTP، احراز هویت
├── agencies/       ← Agency، Branch، AgencyMember
├── listings/       ← فایل‌های ملکی (فاز بعد)
├── crm/            ← درخواست‌ها و مشتریان (فاز بعد)
└── ...
templates/          ← قالب‌های HTML
static/             ← CSS، JS، فونت
```

## متغیرهای محیطی

| متغیر | توضیح | نمونه |
|-------|-------|-------|
| `SECRET_KEY` | کلید محرمانه Django | (تولید با `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`) |
| `DATABASE_URL` | آدرس PostgreSQL | `postgis://user:pass@host/db` |
| `REDIS_URL` | آدرس Redis | `redis://localhost:6379/0` |
| `FIELD_ENCRYPTION_KEY` | کلید Fernet برای رمزنگاری فیلدها | (تولید با `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) |

## ساختار شاخه‌های Git

- `main` — شاخه پایدار
- `phase/1-bootstrap` — فاز ۱ (این شاخه)
- `phase/2-*` — فاز‌های بعدی

هر تسک پس از تکمیل کامیت می‌شود. پیام کامیت طبق Conventional Commits.
