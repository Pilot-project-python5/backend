"""활성 복용 계획의 영양성분 계산 입력 조회."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.care.models import CareItem, CareNutrientSnapshot
from allyakkkuk.curation.models import Nutrient, Product


class DailyIntakePersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class DailyIntakeSource:
    nutrient_id: UUID
    nutrient_code: str
    nutrient_name: str
    canonical_unit: str
    amount_per_unit: Decimal
    unit: str
    dose_per_intake: Decimal
    intakes_per_day: int


class DailyIntakeRepository(Protocol):
    def list_active_nutrient_plans(
        self, *, user_id: UUID
    ) -> tuple[DailyIntakeSource, ...]: ...


class SQLAlchemyDailyIntakeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_active_nutrient_plans(
        self, *, user_id: UUID
    ) -> tuple[DailyIntakeSource, ...]:
        try:
            rows = self._session.execute(
                select(
                    CareNutrientSnapshot.nutrient_id,
                    Nutrient.code,
                    Nutrient.name,
                    Nutrient.canonical_unit,
                    CareNutrientSnapshot.amount_per_unit,
                    CareNutrientSnapshot.unit,
                    CareItem.dose_per_intake,
                    CareItem.intakes_per_day,
                )
                .join(
                    CareItem,
                    CareItem.id == CareNutrientSnapshot.care_item_id,
                )
                .join(Product, Product.id == CareItem.product_id)
                .join(Nutrient, Nutrient.id == CareNutrientSnapshot.nutrient_id)
                .where(
                    CareItem.user_id == user_id,
                    CareItem.deleted_at.is_(None),
                    Product.product_type == "SUPPLEMENT",
                )
                .order_by(Nutrient.code, Nutrient.id, CareItem.id)
            )
            return tuple(
                DailyIntakeSource(
                    nutrient_id=row.nutrient_id,
                    nutrient_code=row.code,
                    nutrient_name=row.name,
                    canonical_unit=row.canonical_unit,
                    amount_per_unit=row.amount_per_unit,
                    unit=row.unit,
                    dose_per_intake=row.dose_per_intake,
                    intakes_per_day=row.intakes_per_day,
                )
                for row in rows
            )
        except SQLAlchemyError as exc:
            raise DailyIntakePersistenceError from exc
