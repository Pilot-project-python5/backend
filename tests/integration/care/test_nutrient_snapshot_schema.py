from __future__ import annotations

import pytest
from sqlalchemy import inspect

from yeongyangkkuk.db.session import engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.2")]


def test_nutrient_snapshot_schema_matches_constraints_and_indexes() -> None:
    inspector = inspect(engine)
    table = "care_nutrient_snapshots"
    columns = {item["name"]: item for item in inspector.get_columns(table)}
    checks = {item["name"] for item in inspector.get_check_constraints(table)}
    foreign_keys = {item["name"]: item for item in inspector.get_foreign_keys(table)}
    uniques = {item["name"] for item in inspector.get_unique_constraints(table)}
    indexes = {
        item["name"]: tuple(item["column_names"])
        for item in inspector.get_indexes(table)
    }

    assert set(columns) == {
        "id",
        "care_item_id",
        "nutrient_id",
        "nutrient_name",
        "amount_per_unit",
        "unit",
    }
    assert all(not item["nullable"] for item in columns.values())
    assert checks >= {
        "ck_care_nutrient_snapshots_name_length",
        "ck_care_nutrient_snapshots_amount",
        "ck_care_nutrient_snapshots_unit",
    }
    assert uniques == {"uq_care_nutrient_snapshots_item_nutrient"}
    assert (
        foreign_keys["fk_care_nutrient_snapshots_care_item_id"]["options"]["ondelete"]
        == "CASCADE"
    )
    assert (
        foreign_keys["fk_care_nutrient_snapshots_nutrient_id"]["options"]["ondelete"]
        == "RESTRICT"
    )
    assert indexes["ix_care_nutrient_snapshots_nutrient_id"] == ("nutrient_id",)
