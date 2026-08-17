from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from yeongyangkkuk.db.session import engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.10")]


def test_0017_medication_details_upgrade_downgrade_round_trip() -> None:
    config = Config("alembic.ini")
    command.downgrade(config, "20260814_0016")
    try:
        assert "medication_details" not in inspect(engine).get_table_names()
        command.upgrade(config, "20260814_0017")
        inspector = inspect(engine)
        assert "medication_details" in inspector.get_table_names()
        assert inspector.get_pk_constraint("medication_details")[
            "constrained_columns"
        ] == ["product_id"]
        command.downgrade(config, "20260814_0016")
        assert "medication_details" not in inspect(engine).get_table_names()
    finally:
        command.upgrade(config, "head")
