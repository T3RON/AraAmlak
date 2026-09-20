.PHONY: up down test lint migrate shell seed build logs ps help

# ظ¤ظ¤ظ¤ ╪ت╪▒╪د ╪د┘à┘╪د┌ر ظ¤ Makefile ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤
# Default target
help:
	@echo "╪ت╪▒╪د ╪د┘à┘╪د┌ر ظ¤ ╪»╪│╪ز┘ê╪▒┘ç╪د█î ┘à┘ê╪ش┘ê╪»:"
	@echo "  make up       - ╪▒╪د┘çظî╪د┘╪»╪د╪▓█î ┘ç┘à┘ç ╪│╪▒┘ê█î╪│ظî┘ç╪د (build + start)"
	@echo "  make down     - ╪ز┘ê┘é┘ ┘ê ╪ص╪░┘ ┌ر╪د┘╪ز█î┘╪▒┘ç╪د"
	@echo "  make test     - ╪د╪ش╪▒╪د█î ╪ز╪│╪زظî┘ç╪د"
	@echo "  make lint     - ╪ذ╪▒╪▒╪│█î ┌ر╪» ╪ذ╪د ruff"
	@echo "  make migrate  - ╪د╪ش╪▒╪د█î migrationظî┘ç╪د"
	@echo "  make shell    - ┘ê╪▒┘ê╪» ╪ذ┘ç Django shell"
	@echo "  make seed     - ╪ذ╪د╪▒┌»╪░╪د╪▒█î ╪»╪د╪»┘çظî┘ç╪د█î ╪د┘ê┘█î┘ç"
	@echo "  make build    - ╪ذ╪د╪▓╪│╪د╪▓█î imageظî┘ç╪د"
	@echo "  make logs     - ┘┘à╪د█î╪┤ ┘╪د┌» ╪│╪▒┘ê█î╪│ web"
	@echo "  make ps       - ┘ê╪╢╪╣█î╪ز ╪│╪▒┘ê█î╪│ظî┘ç╪د"

# ظ¤ظ¤ظ¤ Core targets ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤

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

# ظ¤ظ¤ظ¤ Dev workflow ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤ظ¤

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
