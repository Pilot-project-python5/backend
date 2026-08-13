from __future__ import annotations

import pytest
from sqlalchemy import inspect

from allyakkkuk.db.session import engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.4")]


def test_care_item_soft_delete_schema_matches_contract() -> None:
    inspector = inspect(engine)
    columns = {item["name"]: item for item in inspector.get_columns("care_items")}
    checks = {item["name"] for item in inspector.get_check_constraints("care_items")}
    indexes = {item["name"]: item for item in inspector.get_indexes("care_items")}

    assert columns["deleted_at"]["nullable"] is True
    assert "ck_care_items_deleted_at" in checks
    active_index = indexes["ix_care_items_active_user_created_at"]
    assert active_index["column_names"] == ["user_id", "created_at", "id"]
    predicate = active_index["dialect_options"]["postgresql_where"]
    assert "deleted_at IS NULL" in predicate
