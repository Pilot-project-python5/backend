SHELL := /bin/sh

ENV_FILE ?= .env.local
COMPOSE := docker compose --env-file $(ENV_FILE)
PYTHON ?= python3
POSTGRES_USER ?= allyakkkuk
POSTGRES_PASSWORD ?= allyakkkuk-local
POSTGRES_TEST_DB ?= allyakkkuk_test
TEST_DATABASE_URL ?= postgresql+psycopg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@postgres-test:5432/$(POSTGRES_TEST_DB)

-include $(ENV_FILE)

.PHONY: ensure-env build dev stop migrate seed test test-unit test-integration \
	test-contract feature-new feature-check history-new history-check erd-check \
	openapi openapi-check verify

ensure-env:
	@test -f $(ENV_FILE) || cp .env.example $(ENV_FILE)

build: ensure-env
	$(COMPOSE) build api

dev: ensure-env
	$(COMPOSE) up --build -d postgres-dev postgres-test mail api worker

stop: ensure-env
	$(COMPOSE) down

migrate: ensure-env
	$(COMPOSE) up --wait -d postgres-dev
	$(COMPOSE) run --rm --no-deps api alembic upgrade head

seed: ensure-env
	$(COMPOSE) up --wait -d postgres-dev
	$(COMPOSE) run --rm --no-deps api python -m allyakkkuk.seeding

test: build
	$(COMPOSE) up --wait -d postgres-test
	$(COMPOSE) run --rm --no-deps -e APP_ENV=test -e DATABASE_URL=$(TEST_DATABASE_URL) api pytest -p no:cacheprovider

test-unit: build
	$(COMPOSE) run --rm --no-deps -e APP_ENV=test api pytest -p no:cacheprovider -m unit

test-integration: build
	$(COMPOSE) up --wait -d postgres-test
	$(COMPOSE) run --rm --no-deps -e APP_ENV=test -e DATABASE_URL=$(TEST_DATABASE_URL) api alembic upgrade head
	$(COMPOSE) run --rm --no-deps -e APP_ENV=test -e DATABASE_URL=$(TEST_DATABASE_URL) api pytest -p no:cacheprovider -m integration

test-contract: build
	$(COMPOSE) run --rm --no-deps -e APP_ENV=test api pytest -p no:cacheprovider -m contract

feature-new:
	@test -n "$(FEATURE)" || (echo "FEATURE=F-x.y가 필요합니다" >&2; exit 2)
	$(PYTHON) scripts/harness.py feature-new --feature "$(FEATURE)"

feature-check: build
	@test -n "$(FEATURE)" || (echo "FEATURE=F-x.y가 필요합니다" >&2; exit 2)
	$(COMPOSE) up --wait -d postgres-test
	$(COMPOSE) run --rm --no-deps -e APP_ENV=test -e DATABASE_URL=$(TEST_DATABASE_URL) api \
		alembic upgrade head
	$(COMPOSE) run --rm --no-deps -e APP_ENV=test -e DATABASE_URL=$(TEST_DATABASE_URL) api \
		python scripts/harness.py feature-check --feature "$(FEATURE)" --with-tests

history-new:
	@test -n "$(FEATURE)" || (echo "FEATURE=F-x.y가 필요합니다" >&2; exit 2)
	$(PYTHON) scripts/harness.py history-new --feature "$(FEATURE)"

history-check:
	@test -n "$(FEATURE)" || (echo "FEATURE=F-x.y가 필요합니다" >&2; exit 2)
	$(PYTHON) scripts/harness.py history-check --feature "$(FEATURE)"

erd-check:
	$(PYTHON) .agents/skills/maintain-project-erd/scripts/validate_erd.py

openapi: build
	$(COMPOSE) run --rm --no-deps -e APP_ENV=test api python -m scripts.generate_openapi

openapi-check: build
	$(COMPOSE) run --rm --no-deps -e APP_ENV=test api python -m scripts.check_openapi

verify: build
	$(COMPOSE) up --wait -d postgres-test
	$(COMPOSE) run --rm --no-deps -e APP_ENV=test -e DATABASE_URL=$(TEST_DATABASE_URL) api sh scripts/verify.sh
