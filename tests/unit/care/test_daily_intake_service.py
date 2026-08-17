from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

from yeongyangkkuk.care.daily_intake_repository import (
    DailyIntakePersistenceError,
    DailyIntakeSource,
)
from yeongyangkkuk.care.daily_intake_service import DailyIntakeService
from yeongyangkkuk.core.errors import AppError

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.5")]

USER_ID = UUID("11000000-0000-4000-8000-000000000350")
VITAMIN_C_ID = UUID("23000000-0000-4000-8000-000000000350")
VITAMIN_D_ID = UUID("23000000-0000-4000-8000-000000000351")


class StubDailyIntakeRepository:
    def __init__(
        self,
        rows: tuple[DailyIntakeSource, ...] = (),
        *,
        fails: bool = False,
    ) -> None:
        self.rows = rows
        self.fails = fails
        self.calls: list[UUID] = []

    def list_active_nutrient_plans(
        self, *, user_id: UUID
    ) -> tuple[DailyIntakeSource, ...]:
        self.calls.append(user_id)
        if self.fails:
            raise DailyIntakePersistenceError
        return self.rows


def source(
    nutrient_id: UUID,
    code: str,
    *,
    canonical_unit: str,
    amount: str,
    unit: str,
    dose: str = "1",
    times: int = 1,
) -> DailyIntakeSource:
    return DailyIntakeSource(
        nutrient_id=nutrient_id,
        nutrient_code=code,
        nutrient_name=f"{code} 이름",
        canonical_unit=canonical_unit,
        amount_per_unit=Decimal(amount),
        unit=unit,
        dose_per_intake=Decimal(dose),
        intakes_per_day=times,
    )


def test_calculates_converts_and_aggregates_daily_plan_without_rounding() -> None:
    repository = StubDailyIntakeRepository(
        (
            source(
                VITAMIN_C_ID,
                "VITAMIN_C",
                canonical_unit="MG",
                amount="1",
                unit="G",
                dose="2",
            ),
            source(
                VITAMIN_C_ID,
                "VITAMIN_C",
                canonical_unit="MG",
                amount="500",
                unit="MG",
                times=2,
            ),
            source(
                VITAMIN_C_ID,
                "VITAMIN_C",
                canonical_unit="MG",
                amount="250000",
                unit="MCG",
            ),
            source(
                VITAMIN_D_ID,
                "VITAMIN_D",
                canonical_unit="IU",
                amount="400",
                unit="IU",
                dose="0.5",
                times=2,
            ),
        )
    )

    result = DailyIntakeService(repository).get_daily_intake(user_id=USER_ID)

    assert repository.calls == [USER_ID]
    assert [(item.nutrient_code, item.daily_amount, item.unit) for item in result] == [
        ("VITAMIN_C", Decimal("3250"), "MG"),
        ("VITAMIN_D", Decimal("400.0"), "IU"),
    ]


@pytest.mark.parametrize(
    ("amount", "unit", "canonical_unit", "expected"),
    [
        ("1", "G", "MCG", Decimal("1000000")),
        ("1000", "MG", "G", Decimal("1")),
        ("1000", "MCG", "MG", Decimal("1")),
        ("2.5", "MG", "MCG", Decimal("2500.0")),
    ],
)
def test_converts_all_supported_mass_unit_directions(
    amount: str,
    unit: str,
    canonical_unit: str,
    expected: Decimal,
) -> None:
    repository = StubDailyIntakeRepository(
        (
            source(
                VITAMIN_C_ID,
                "VITAMIN_C",
                canonical_unit=canonical_unit,
                amount=amount,
                unit=unit,
            ),
        )
    )

    result = DailyIntakeService(repository).get_daily_intake(user_id=USER_ID)

    assert result[0].daily_amount == expected


def test_returns_empty_result_when_no_active_nutrient_plan_exists() -> None:
    assert (
        DailyIntakeService(StubDailyIntakeRepository()).get_daily_intake(
            user_id=USER_ID
        )
        == ()
    )


@pytest.mark.parametrize(
    ("unit", "canonical_unit"),
    [("IU", "MG"), ("MCG", "IU")],
)
def test_rejects_incompatible_iu_and_mass_units(
    unit: str,
    canonical_unit: str,
) -> None:
    repository = StubDailyIntakeRepository(
        (
            source(
                VITAMIN_D_ID,
                "VITAMIN_D",
                canonical_unit=canonical_unit,
                amount="10",
                unit=unit,
            ),
        )
    )

    with pytest.raises(AppError) as raised:
        DailyIntakeService(repository).get_daily_intake(user_id=USER_ID)

    assert raised.value.status_code == 503
    assert raised.value.code == "SERVICE_UNAVAILABLE"


def test_maps_repository_failure_to_service_unavailable() -> None:
    with pytest.raises(AppError) as raised:
        DailyIntakeService(StubDailyIntakeRepository(fails=True)).get_daily_intake(
            user_id=USER_ID
        )

    assert raised.value.status_code == 503
    assert raised.value.code == "SERVICE_UNAVAILABLE"
