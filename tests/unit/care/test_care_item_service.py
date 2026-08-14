from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from allyakkkuk.care.care_item_repository import (
    CareItemCreateData,
    CareItemPersistenceError,
    CareItemRecord,
    CareItemRepository,
)
from allyakkkuk.care.care_item_service import (
    CareItemRegistrationCommand,
    CareItemService,
)
from allyakkkuk.core.errors import AppError
from allyakkkuk.ports.clock import FakeClock

pytestmark = [
    pytest.mark.unit,
    pytest.mark.feature("F-3.1"),
    pytest.mark.feature("F-3.7"),
    pytest.mark.feature("F-3.11"),
]

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000031")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000031")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000031")
SEOUL = ZoneInfo("Asia/Seoul")


class FakeCareItemRepository(CareItemRepository):
    def __init__(
        self,
        result: CareItemRecord | None,
        *,
        fails: bool = False,
    ) -> None:
        self.result = result
        self.fails = fails
        self.calls: list[CareItemCreateData] = []

    def create(self, data: CareItemCreateData) -> CareItemRecord | None:
        self.calls.append(data)
        if self.fails:
            raise CareItemPersistenceError
        return self.result


def command() -> CareItemRegistrationCommand:
    return CareItemRegistrationCommand(
        product_id=PRODUCT_ID,
        purchase_date=date(2026, 8, 10),
        intake_start_date=date(2026, 8, 12),
        total_quantity=Decimal("60"),
        dose_per_intake=Decimal("1.5"),
        intakes_per_day=2,
        expiration_date=date(2027, 1, 31),
    )


def record() -> CareItemRecord:
    value = command()
    return CareItemRecord(
        id=ITEM_ID,
        user_id=USER_ID,
        product_id=value.product_id,
        purchase_date=value.purchase_date,
        intake_start_date=value.intake_start_date,
        expected_depletion_date=date(2026, 8, 31),
        total_quantity=value.total_quantity,
        quantity_unit="CAPSULE",
        dose_per_intake=value.dose_per_intake,
        intakes_per_day=value.intakes_per_day,
        created_at=NOW,
        expiration_date=value.expiration_date,
    )


def test_register_creates_user_owned_care_item_with_server_time() -> None:
    repository = FakeCareItemRepository(record())

    result = CareItemService(repository, FakeClock(NOW), SEOUL).register(
        user_id=USER_ID,
        command=command(),
    )

    assert result.id == ITEM_ID
    assert result.total_quantity == Decimal("60")
    assert result.quantity_unit == "CAPSULE"
    assert result.expected_depletion_date == date(2026, 8, 31)
    assert result.expiration_date == date(2027, 1, 31)
    assert repository.calls == [
        CareItemCreateData(
            user_id=USER_ID,
            product_id=PRODUCT_ID,
            purchase_date=date(2026, 8, 10),
            intake_start_date=date(2026, 8, 12),
            expected_depletion_date=date(2026, 8, 31),
            total_quantity=Decimal("60"),
            dose_per_intake=Decimal("1.5"),
            intakes_per_day=2,
            created_at=NOW,
            expiration_date=date(2027, 1, 31),
        )
    ]


@pytest.mark.parametrize(
    ("invalid", "field", "code"),
    [
        (
            replace(command(), purchase_date=date(2026, 8, 13)),
            "body.purchase_date",
            "purchase_date_future",
        ),
        (
            replace(command(), intake_start_date=date(2026, 8, 9)),
            "body.intake_start_date",
            "intake_start_before_purchase",
        ),
        (
            replace(command(), dose_per_intake=Decimal("61")),
            "body.dose_per_intake",
            "dose_exceeds_total_quantity",
        ),
    ],
)
def test_register_rejects_cross_field_rules_before_database(
    invalid: CareItemRegistrationCommand,
    field: str,
    code: str,
) -> None:
    repository = FakeCareItemRepository(record())

    with pytest.raises(AppError) as captured:
        CareItemService(repository, FakeClock(NOW), SEOUL).register(
            user_id=USER_ID,
            command=invalid,
        )

    assert captured.value.status_code == 422
    assert captured.value.code == "VALIDATION_FAILED"
    assert captured.value.fields[0].field == field
    assert captured.value.fields[0].code == code
    assert repository.calls == []


def test_register_maps_missing_catalog_product_to_not_found() -> None:
    service = CareItemService(FakeCareItemRepository(None), FakeClock(NOW), SEOUL)

    with pytest.raises(AppError) as captured:
        service.register(user_id=USER_ID, command=command())

    assert captured.value.status_code == 404
    assert captured.value.code == "PRODUCT_NOT_FOUND"


def test_register_maps_database_failure_to_service_unavailable() -> None:
    service = CareItemService(
        FakeCareItemRepository(None, fails=True),
        FakeClock(NOW),
        SEOUL,
    )

    with pytest.raises(AppError) as captured:
        service.register(user_id=USER_ID, command=command())

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"


def test_purchase_date_uses_configured_local_date_near_utc_midnight() -> None:
    near_midnight = datetime(2026, 8, 11, 15, 30, tzinfo=UTC)
    local_today = replace(
        command(),
        purchase_date=date(2026, 8, 12),
        intake_start_date=date(2026, 8, 12),
    )
    repository = FakeCareItemRepository(record())

    CareItemService(repository, FakeClock(near_midnight), SEOUL).register(
        user_id=USER_ID,
        command=local_today,
    )

    assert repository.calls[0].purchase_date == date(2026, 8, 12)


def test_register_rejects_plan_beyond_supported_date_range() -> None:
    invalid = replace(
        command(),
        total_quantity=Decimal("999999999.999"),
        dose_per_intake=Decimal("0.001"),
        intakes_per_day=1,
    )
    repository = FakeCareItemRepository(record())

    with pytest.raises(AppError) as captured:
        CareItemService(repository, FakeClock(NOW), SEOUL).register(
            user_id=USER_ID,
            command=invalid,
        )

    assert captured.value.status_code == 422
    assert captured.value.fields[0].code == "depletion_date_out_of_range"
    assert repository.calls == []
