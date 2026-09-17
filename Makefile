# Common tasks. Everything backend-related runs inside Docker, so you don't need Python 3.12 installed locally.
.PHONY: help install dev up down logs migrate seed validate-bank export-bank create-admin test test-backend test-frontend e2e build

COMPOSE = docker compose
API = $(COMPOSE) run --rm api

help:
	@echo "make install        Build the API image and install frontend packages"
	@echo "make dev            Start MySQL, the API (with reload) and the Vite dev server"
	@echo "make down           Stop everything"
	@echo "make migrate        Run database migrations"
	@echo "make seed           Load task types and the question bank (safe to repeat)"
	@echo "make validate-bank  Check every question bank file"
	@echo "make export-bank    Write the whole bank to bank-export.json"
	@echo "make create-admin EMAIL=you@example.com NAME='Your Name'"
	@echo "make test           Run backend and frontend tests"
	@echo "make e2e            Run the Playwright smoke test (needs make dev running)"

install:
	$(COMPOSE) build api
	cd frontend && npm ci

dev:
	$(COMPOSE) up -d db api
	$(COMPOSE) up web

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api

migrate:
	$(API) alembic upgrade head

seed:
	$(API) python -m scripts.seed

validate-bank:
	$(API) python -m scripts.validate_bank

export-bank:
	$(API) python -m scripts.export_bank --out /app/backend/bank-export.json
	mv backend/bank-export.json ./bank-export.json

create-admin:
	$(COMPOSE) run --rm -it api python -m scripts.create_admin --email "$(EMAIL)" --name "$(NAME)"

test: test-backend test-frontend

test-backend:
	$(API) pytest

test-frontend:
	cd frontend && npm test

e2e:
	cd frontend && npx playwright install chromium && npm run e2e

build:
	cd frontend && npm run build
