#!/bin/sh
set -eu

export COVERAGE_FILE="${COVERAGE_FILE:-/tmp/allyakkkuk.coverage}"
export MYPY_CACHE_DIR="${MYPY_CACHE_DIR:-/tmp/allyakkkuk-mypy-cache}"
export RUFF_CACHE_DIR="${RUFF_CACHE_DIR:-/tmp/allyakkkuk-ruff-cache}"

ruff format --check .
ruff check .
mypy
python .agents/skills/maintain-project-erd/scripts/validate_erd.py
alembic upgrade head
alembic check
python -m allyakkkuk.seeding
python -m allyakkkuk.seeding
pytest -p no:cacheprovider --cov=allyakkkuk --cov-report=term-missing
python -m scripts.check_openapi
