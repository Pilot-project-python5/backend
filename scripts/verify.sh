#!/bin/sh
set -eu

export COVERAGE_FILE="${COVERAGE_FILE:-/tmp/yeongyangkkuk.coverage}"
export MYPY_CACHE_DIR="${MYPY_CACHE_DIR:-/tmp/yeongyangkkuk-mypy-cache}"
export RUFF_CACHE_DIR="${RUFF_CACHE_DIR:-/tmp/yeongyangkkuk-ruff-cache}"

ruff format --check .
ruff check .
mypy
python .agents/skills/maintain-project-erd/scripts/validate_erd.py
alembic upgrade head
alembic check
python -m yeongyangkkuk.seeding
python -m yeongyangkkuk.seeding
pytest -p no:cacheprovider --cov=yeongyangkkuk --cov-report=term-missing
python -m scripts.check_openapi
