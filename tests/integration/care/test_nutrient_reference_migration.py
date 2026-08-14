from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from allyakkkuk.db.session import engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.6")]


def test_0015_upgrade_and_downgrade_only_reference_tables() -> None:
    config = Config("alembic.ini")
    command.downgrade(config, "20260813_0014")
    try:
        tables = set(inspect(engine).get_table_names())
        assert "nutrient_reference_versions" not in tables
        assert "nutrient_reference_values" not in tables
        assert {"users", "products", "care_items"} <= tables
        command.upgrade(config, "head")
        tables = set(inspect(engine).get_table_names())
        assert {"nutrient_reference_versions", "nutrient_reference_values"} <= tables
    finally:
        command.upgrade(config, "head")
