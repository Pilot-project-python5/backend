"""복용 계획 기준 일일 예정 섭취량 계산."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from yeongyangkkuk.care.daily_intake_repository import (
    DailyIntakePersistenceError,
    DailyIntakeRepository,
)
from yeongyangkkuk.core.errors import AppError

_MASS_IN_MCG = {
    "G": Decimal("1000000"),
    "MG": Decimal("1000"),
    "MCG": Decimal("1"),
}


@dataclass(frozen=True, slots=True)
class DailyIntakeItem:
    nutrient_id: UUID
    nutrient_code: str
    nutrient_name: str
    daily_amount: Decimal
    unit: str


class DailyIntakeService:
    def __init__(self, repository: DailyIntakeRepository) -> None:
        self._repository = repository

    def get_daily_intake(self, *, user_id: UUID) -> tuple[DailyIntakeItem, ...]:
        try:
            sources = self._repository.list_active_nutrient_plans(user_id=user_id)
            totals: dict[UUID, DailyIntakeItem] = {}
            for source in sources:
                planned_amount = (
                    source.amount_per_unit
                    * source.dose_per_intake
                    * source.intakes_per_day
                )
                converted = _convert_unit(
                    planned_amount,
                    source_unit=source.unit,
                    target_unit=source.canonical_unit,
                )
                existing = totals.get(source.nutrient_id)
                if existing is None:
                    totals[source.nutrient_id] = DailyIntakeItem(
                        nutrient_id=source.nutrient_id,
                        nutrient_code=source.nutrient_code,
                        nutrient_name=source.nutrient_name,
                        daily_amount=converted,
                        unit=source.canonical_unit,
                    )
                else:
                    totals[source.nutrient_id] = DailyIntakeItem(
                        nutrient_id=existing.nutrient_id,
                        nutrient_code=existing.nutrient_code,
                        nutrient_name=existing.nutrient_name,
                        daily_amount=existing.daily_amount + converted,
                        unit=existing.unit,
                    )
        except (DailyIntakePersistenceError, ValueError) as exc:
            raise _service_unavailable() from exc

        return tuple(
            sorted(
                totals.values(),
                key=lambda item: (item.nutrient_code, item.nutrient_id),
            )
        )


def _convert_unit(
    amount: Decimal,
    *,
    source_unit: str,
    target_unit: str,
) -> Decimal:
    if source_unit == target_unit:
        return amount
    if source_unit in _MASS_IN_MCG and target_unit in _MASS_IN_MCG:
        amount_in_mcg = amount * _MASS_IN_MCG[source_unit]
        return amount_in_mcg / _MASS_IN_MCG[target_unit]
    raise ValueError("서로 변환할 수 없는 영양성분 단위입니다.")


def _service_unavailable() -> AppError:
    return AppError(
        status_code=503,
        code="SERVICE_UNAVAILABLE",
        message="서비스가 아직 준비되지 않았습니다.",
    )
