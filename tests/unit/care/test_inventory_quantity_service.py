from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from allyakkkuk.care.care_item_repository import (
    CareItemCreateData,
    CareItemRecord,
    CareItemRepository,
)
from allyakkkuk.care.care_item_service import (
    CareItemRegistrationCommand,
    CareItemService,
)
from allyakkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.3")]

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000208")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000208")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000208")


class InventoryRepository(CareItemRepository):
    def __init__(self, result: CareItemRecord) -> None:
        self.result = result
        self.calls: list[CareItemCreateData] = []

    def create(self, data: CareItemCreateData) -> CareItemRecord | None:
        self.calls.append(data)
        return self.result


def test_registration_returns_server_snapshotted_quantity_unit() -> None:
    repository = InventoryRepository(
        CareItemRecord(
            id=ITEM_ID,
            user_id=USER_ID,
            product_id=PRODUCT_ID,
            purchase_date=date(2026, 8, 10),
            intake_start_date=date(2026, 8, 12),
            expected_depletion_date=date(2026, 8, 23),
            total_quantity=Decimal("24"),
            quantity_unit="PACKET",
            dose_per_intake=Decimal("1"),
            intakes_per_day=2,
            created_at=NOW,
        )
    )
    command = CareItemRegistrationCommand(
        product_id=PRODUCT_ID,
        purchase_date=date(2026, 8, 10),
        intake_start_date=date(2026, 8, 12),
        total_quantity=Decimal("24"),
        dose_per_intake=Decimal("1"),
        intakes_per_day=2,
    )

    result = CareItemService(
        repository,
        FakeClock(NOW),
        ZoneInfo("Asia/Seoul"),
    ).register(user_id=USER_ID, command=command)

    assert result.quantity_unit == "PACKET"
    assert repository.calls[0].total_quantity == Decimal("24")
