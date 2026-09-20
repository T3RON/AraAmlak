.PHONY: up down test lint migrate shell seed build logs ps help

# ─── آرا املاک — Makefile ──────────────────────────────────────────────────────
# Default target
help:
	@echo "آرا املاک — دستورهای موجود:"
	@echo "  make up       - راه‌اندازی همه سرویس‌ها (build + start)"
	@echo "  make down     - توقف و حذف کانتینرها"
	@echo "  make test     - اجرای تست‌ها"
	@echo "  make lint     - بررسی کد با ruff"
	@echo "  make migrate  - اجرای migration‌ها"
	@echo "  make shell    - ورود به Django shell"
	@echo "  make seed     - بارگذاری داده‌های اولیه"
	@echo "  make build    - بازسازی image‌ها"
	@echo "  make logs     - نمایش لاگ سرویس web"
	@echo "  make ps       - وضعیت سرویس‌ها"

# ─── Core targets ─────────────────────────────────────────────────────────────

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f web

ps:
	docker compose ps

# ─── Dev workflow ─────────────────────────────────────────────────────────────

test:
	docker compose run --rm web pytest -v --tb=short

lint:
	docker compose run --rm web ruff check .

migrate:
	docker compose run --rm web python manage.py migrate --noinput

shell:
	docker compose run --rm web python manage.py shell

seed:
	docker compose run --rm web python manage.py seed
