from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from allyakkkuk.care.care_item_repository import (
    CareItemListRecord,
    CareItemManagementRepository,
    CareItemPageRecord,
    CareItemPersistenceError,
)
from allyakkkuk.care.care_item_service import CareItemManagementService
from allyakkkuk.core.errors import AppError
from allyakkkuk.ports.clock import FakeClock

pytestmark = [
    pytest.mark.unit,
    pytest.mark.feature("F-3.4"),
    pytest.mark.feature("F-3.11"),
    pytest.mark.feature("F-3.8"),
]

NOW = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000214")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000214")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000214")


def item_record() -> CareItemListRecord:
    return CareItemListRecord(
        id=ITEM_ID,
        product_id=PRODUCT_ID,
        product_type="SUPPLEMENT",
        brand="목록 단위 브랜드",
        name="목록 단위 제품",
        image_url="/static/products/care-list-unit-214.svg",
        purchase_date=date(2026, 8, 10),
        intake_start_date=date(2026, 8, 13),
        expected_depletion_date=date(2026, 9, 11),
        total_quantity=Decimal("60"),
        quantity_unit="CAPSULE",
        dose_per_intake=Decimal("1"),
        intakes_per_day=2,
        created_at=NOW,
        expiration_date=date(2026, 8, 18),
    )


class StubManagementRepository(CareItemManagementRepository):
    def __init__(self) -> None:
        self.page = CareItemPageRecord(items=(item_record(),), total=21)
        self.deleted = True
        self.list_error = False
        self.delete_error = False
        self.expiration_error = False
        self.list_calls: list[tuple[UUID, int, int]] = []
        self.delete_calls: list[tuple[UUID, UUID, datetime]] = []
        self.expiration_calls: list[tuple[UUID, UUID, date, datetime]] = []

    def list_active(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
    ) -> CareItemPageRecord:
        self.list_calls.append((user_id, page, page_size))
        if self.list_error:
            raise CareItemPersistenceError
        return self.page

    def soft_delete(
        self,
        *,
        user_id: UUID,
        care_item_id: UUID,
        deleted_at: datetime,
    ) -> bool:
        self.delete_calls.append((user_id, care_item_id, deleted_at))
        if self.delete_error:
            raise CareItemPersistenceError
        return self.deleted

    def update_expiration(
        self,
        *,
        user_id: UUID,
        care_item_id: UUID,
        expiration_date: date,
        updated_at: datetime,
    ) -> bool:
        self.expiration_calls.append(
            (user_id, care_item_id, expiration_date, updated_at)
        )
        if self.expiration_error:
            raise CareItemPersistenceError
        return self.deleted


def test_list_items_maps_active_page_and_has_next() -> None:
    repository = StubManagementRepository()

    result = CareItemManagementService(
        repository, FakeClock(NOW), ZoneInfo("Asia/Seoul")
    ).list_items(
        user_id=USER_ID,
        page=1,
        page_size=20,
    )

    assert result.items[0].id == ITEM_ID
    assert result.items[0].quantity_unit == "CAPSULE"
    assert result.items[0].days_until_depletion == 29
    assert result.items[0].inventory_status == "NORMAL"
    assert result.items[0].days_until_expiration == 5
    assert result.items[0].expiration_status == "EXPIRING_SOON"
    assert result.page == 1
    assert result.page_size == 20
    assert result.total == 21
    assert result.has_next is True
    assert repository.list_calls == [(USER_ID, 1, 20)]


def test_delete_item_uses_server_time_and_hides_missing_ownership() -> None:
    repository = StubManagementRepository()
    service = CareItemManagementService(
        repository, FakeClock(NOW), ZoneInfo("Asia/Seoul")
    )

    service.delete_item(user_id=USER_ID, care_item_id=ITEM_ID)

    assert repository.delete_calls == [(USER_ID, ITEM_ID, NOW)]

    repository.deleted = False
    with pytest.raises(AppError) as captured:
        service.delete_item(user_id=USER_ID, care_item_id=ITEM_ID)

    assert captured.value.status_code == 404
    assert captured.value.code == "CARE_ITEM_NOT_FOUND"


def test_update_expiration_uses_server_time_and_hides_missing_ownership() -> None:
    repository = StubManagementRepository()
    service = CareItemManagementService(
        repository, FakeClock(NOW), ZoneInfo("Asia/Seoul")
    )
    expiration_date = date(2027, 1, 31)

    service.update_expiration(
        user_id=USER_ID,
        care_item_id=ITEM_ID,
        expiration_date=expiration_date,
    )

    assert repository.expiration_calls == [(USER_ID, ITEM_ID, expiration_date, NOW)]

    repository.deleted = False
    with pytest.raises(AppError) as captured:
        service.update_expiration(
            user_id=USER_ID,
            care_item_id=ITEM_ID,
            expiration_date=expiration_date,
        )

    assert captured.value.status_code == 404
    assert captured.value.code == "CARE_ITEM_NOT_FOUND"


@pytest.mark.parametrize("operation", ["list", "delete", "expiration"])
def test_management_persistence_failure_becomes_service_unavailable(
    operation: str,
) -> None:
    repository = StubManagementRepository()
    repository.list_error = operation == "list"
    repository.delete_error = operation == "delete"
    repository.expiration_error = operation == "expiration"
    service = CareItemManagementService(
        repository, FakeClock(NOW), ZoneInfo("Asia/Seoul")
    )

    with pytest.raises(AppError) as captured:
        if operation == "list":
            service.list_items(user_id=USER_ID, page=1, page_size=20)
        elif operation == "delete":
            service.delete_item(user_id=USER_ID, care_item_id=ITEM_ID)
        else:
            service.update_expiration(
                user_id=USER_ID,
                care_item_id=ITEM_ID,
                expiration_date=date(2027, 1, 31),
            )

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"
