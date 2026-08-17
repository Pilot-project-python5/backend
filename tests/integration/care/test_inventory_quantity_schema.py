from __future__ import annotations

import pytest
from sqlalchemy import inspect

from yeongyangkkuk.db.session import engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.3")]


def test_care_item_quantity_unit_schema_matches_contract() -> None:
    inspector = inspect(engine)
    columns = {item["name"]: item for item in inspector.get_columns("care_items")}
    checks = {item["name"] for item in inspector.get_check_constraints("care_items")}

    assert columns["quantity_unit"]["nullable"] is False
    assert "ck_care_items_quantity_unit" in checks
    assert "quantity_unit" not in {
        column
        for index in inspector.get_indexes("care_items")
        for column in index["column_names"]
    }
