COMPOSE = docker compose -f infra/compose.yaml
COMPOSE_DEV = $(COMPOSE) -f infra/compose.dev.yaml
COMPOSE_PROD = $(COMPOSE) -f infra/compose.prod.yaml
PYTHON ?= python3.12

.PHONY: up up-dev down logs ps build test quality seed-research seed-research-demo seed-research-check migration prod-config prod-up tls-init

up:
	$(COMPOSE) up -d --build

up-dev:
	$(COMPOSE_DEV) up -d --build

down:
	$(COMPOSE_DEV) down

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

build:
	$(COMPOSE) build

quality:
	./scripts/quality_gate.sh

seed-research:
	$(PYTHON) scripts/build_catalog_seed.py
	$(COMPOSE_DEV) run --rm --build api python scripts/seed_catalog.py seeds/research_batches --preserve-existing

seed-research-demo:
	$(PYTHON) scripts/build_catalog_seed.py --demo
	$(COMPOSE_DEV) run --rm --build api python scripts/seed_catalog.py seeds/research_demo_batches --preserve-existing

seed-research-check:
	$(PYTHON) scripts/build_catalog_seed.py --check
	$(PYTHON) scripts/build_catalog_seed.py --demo --check

test:
	docker build --target quality -t product-hackathon-backend-quality ./backend
	cd frontend && npm run test:run

migration:
	@test -n "$(name)" || (echo 'Usage: make migration name="add users"' && exit 1)
	$(COMPOSE_DEV) run --rm api python scripts/create_migration.py "$(name)"

prod-config:
	$(COMPOSE_PROD) config --quiet

prod-up:
	$(COMPOSE_PROD) --profile tls up -d --build

tls-init:
	$(COMPOSE) --profile tls-init run --rm --build certbot-init
