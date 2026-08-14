"""사용자 복용 계획과 공인 기준량 비교."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from allyakkkuk.care.daily_intake_service import DailyIntakeService
from allyakkkuk.care.nutrient_status_repository import (
    NutrientStatusPersistenceError,
    NutrientStatusRepository,
)
from allyakkkuk.core.errors import AppError
from allyakkkuk.ports.clock import Clock


@dataclass(frozen=True, slots=True)
class NutrientStatusItem:
    nutrient_id: UUID
    nutrient_code: str
    nutrient_name: str
    daily_amount: Decimal
    unit: str
    reference_available: bool
    reference_amount: Decimal | None
    reference_type: str | None
    achievement_rate_percent: Decimal | None


@dataclass(frozen=True, slots=True)
class NutrientStatusResult:
    as_of_date: date
    age: int
    gender: str
    reference_version: str
    reference_source_name: str
    reference_source_url: str
    nutrients: tuple[NutrientStatusItem, ...]


class NutrientStatusService:
    def __init__(
        self,
        *,
        repository: NutrientStatusRepository,
        daily_intake_service: DailyIntakeService,
        clock: Clock,
        time_zone: ZoneInfo,
        reference_version: str,
    ) -> None:
        self._repository = repository
        self._daily_intake_service = daily_intake_service
        self._clock = clock
        self._time_zone = time_zone
        self._reference_version = reference_version

    def get_status(self, *, user_id: UUID) -> NutrientStatusResult:
        try:
            profile = self._repository.get_profile(user_id=user_id)
            as_of_date = self._clock.now().astimezone(self._time_zone).date()
            age = _completed_age(profile.birth_date, as_of_date)
            version = self._repository.get_reference_version(
                version=self._reference_version
            )
            if version is None:
                raise NutrientStatusPersistenceError
            references = self._repository.list_reference_values(
                version_id=version.id, gender=profile.gender, age=age
            )
            reference_by_nutrient = {row.nutrient_id: row for row in references}
            nutrients = []
            for current in self._daily_intake_service.get_daily_intake(user_id=user_id):
                reference = reference_by_nutrient.get(current.nutrient_id)
                if reference is None:
                    nutrients.append(
                        NutrientStatusItem(
                            current.nutrient_id,
                            current.nutrient_code,
                            current.nutrient_name,
                            current.daily_amount,
                            current.unit,
                            False,
                            None,
                            None,
                            None,
                        )
                    )
                    continue
                if reference.unit != current.unit:
                    raise NutrientStatusPersistenceError
                rate = (
                    current.daily_amount / reference.reference_amount * Decimal("100")
                ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
                nutrients.append(
                    NutrientStatusItem(
                        current.nutrient_id,
                        current.nutrient_code,
                        current.nutrient_name,
                        current.daily_amount,
                        current.unit,
                        True,
                        reference.reference_amount,
                        reference.reference_type,
                        rate,
                    )
                )
            return NutrientStatusResult(
                as_of_date,
                age,
                profile.gender,
                version.version,
                version.source_name,
                version.source_url,
                tuple(nutrients),
            )
        except NutrientStatusPersistenceError as exc:
            raise AppError(
                status_code=503,
                code="SERVICE_UNAVAILABLE",
                message="서비스가 아직 준비되지 않았습니다.",
            ) from exc


def _completed_age(birth_date: date, today: date) -> int:
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )
