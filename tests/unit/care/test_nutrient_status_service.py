from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from yeongyangkkuk.care.daily_intake_service import DailyIntakeItem
from yeongyangkkuk.care.nutrient_status_repository import (
    NutrientReferenceRecord,
    NutrientReferenceVersionRecord,
    NutrientStatusProfile,
)
from yeongyangkkuk.care.nutrient_status_service import NutrientStatusService
from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.6")]

USER_ID = UUID("11000000-0000-4000-8000-000000000360")
VITAMIN_C_ID = UUID("23000000-0000-4000-8000-000000000001")
OMEGA_ID = UUID("23000000-0000-4000-8000-000000000004")
VERSION_ID = UUID("36000000-0000-4000-8000-000000000001")


class StubDailyIntakeService:
    def get_daily_intake(self, *, user_id: UUID) -> tuple[DailyIntakeItem, ...]:
        assert user_id == USER_ID
        return (
            DailyIntakeItem(
                VITAMIN_C_ID, "VITAMIN_C", "비타민 C", Decimal("150"), "MG"
            ),
            DailyIntakeItem(OMEGA_ID, "OMEGA_3", "오메가3", Decimal("1040"), "MG"),
        )


class StubRepository:
    def __init__(
        self, *, birth_date: date = date(2000, 8, 15), version_exists: bool = True
    ) -> None:
        self.birth_date = birth_date
        self.version_exists = version_exists

    def get_profile(self, *, user_id: UUID) -> NutrientStatusProfile:
        assert user_id == USER_ID
        return NutrientStatusProfile(birth_date=self.birth_date, gender="FEMALE")

    def get_reference_version(
        self, *, version: str
    ) -> NutrientReferenceVersionRecord | None:
        assert version == "KDRI-2025-20260316"
        if not self.version_exists:
            return None
        return NutrientReferenceVersionRecord(
            id=VERSION_ID,
            version=version,
            source_name="2025 한국인 영양소 섭취기준",
            source_url="https://example.com/kdri",
        )

    def list_reference_values(
        self, *, version_id: UUID, gender: str, age: int
    ) -> tuple[NutrientReferenceRecord, ...]:
        assert (version_id, gender) == (VERSION_ID, "FEMALE")
        assert age in {25, 26}
        return (
            NutrientReferenceRecord(
                nutrient_id=VITAMIN_C_ID,
                nutrient_code="VITAMIN_C",
                reference_type="RNI",
                reference_amount=Decimal("100"),
                unit="MG",
            ),
        )


def service(repository: StubRepository) -> NutrientStatusService:
    return NutrientStatusService(
        repository=repository,
        daily_intake_service=StubDailyIntakeService(),  # type: ignore[arg-type]
        clock=FakeClock(datetime(2026, 8, 14, 15, 0, tzinfo=UTC)),
        time_zone=ZoneInfo("Asia/Seoul"),
        reference_version="KDRI-2025-20260316",
    )


def test_compares_plan_with_reference_and_keeps_missing_reference() -> None:
    result = service(StubRepository()).get_status(user_id=USER_ID)

    assert (result.as_of_date, result.age, result.gender) == (
        date(2026, 8, 15),
        26,
        "FEMALE",
    )
    assert result.nutrients[0].achievement_rate_percent == Decimal("150.0")
    assert result.nutrients[0].reference_type == "RNI"
    assert result.nutrients[1].reference_available is False
    assert result.nutrients[1].reference_amount is None
    assert result.nutrients[1].achievement_rate_percent is None


def test_uses_completed_age_before_birthday() -> None:
    result = service(StubRepository(birth_date=date(2000, 8, 16))).get_status(
        user_id=USER_ID
    )
    assert result.age == 25


def test_missing_configured_reference_version_is_service_unavailable() -> None:
    with pytest.raises(AppError) as raised:
        service(StubRepository(version_exists=False)).get_status(user_id=USER_ID)
    assert (raised.value.status_code, raised.value.code) == (503, "SERVICE_UNAVAILABLE")
