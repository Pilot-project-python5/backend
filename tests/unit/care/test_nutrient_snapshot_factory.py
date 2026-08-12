from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

from allyakkkuk.care.care_item_repository import (
    NutrientSnapshotSource,
    build_nutrient_snapshots,
)

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.2")]

CARE_ITEM_ID = UUID("31000000-0000-4000-8000-000000000201")
NUTRIENT_ID = UUID("23000000-0000-4000-8000-000000000201")


def test_build_nutrient_snapshots_copies_catalog_values_to_new_item() -> None:
    source = NutrientSnapshotSource(
        nutrient_id=NUTRIENT_ID,
        nutrient_name="비타민 C",
        amount_per_unit=Decimal("235.1250"),
        unit="MG",
    )

    snapshots = build_nutrient_snapshots(CARE_ITEM_ID, (source,))

    assert len(snapshots) == 1
    assert snapshots[0].care_item_id == CARE_ITEM_ID
    assert snapshots[0].nutrient_id == NUTRIENT_ID
    assert snapshots[0].nutrient_name == "비타민 C"
    assert snapshots[0].amount_per_unit == Decimal("235.1250")
    assert snapshots[0].unit == "MG"


def test_build_nutrient_snapshots_accepts_empty_active_catalog() -> None:
    assert build_nutrient_snapshots(CARE_ITEM_ID, ()) == ()
