"""복용 제품 등록 저장소 포트와 PostgreSQL 구현."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.care.models import CareItem
from allyakkkuk.curation.models import Product


class CareItemPersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class CareItemCreateData:
    user_id: UUID
    product_id: UUID
    purchase_date: date
    intake_start_date: date
    total_quantity: Decimal
    dose_per_intake: Decimal
    intakes_per_day: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CareItemRecord:
    id: UUID
    user_id: UUID
    product_id: UUID
    purchase_date: date
    intake_start_date: date
    total_quantity: Decimal
    dose_per_intake: Decimal
    intakes_per_day: int
    created_at: datetime


class CareItemRepository(Protocol):
    def create(self, data: CareItemCreateData) -> CareItemRecord | None: ...


class SQLAlchemyCareItemRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, data: CareItemCreateData) -> CareItemRecord | None:
        try:
            product_id = self._session.scalar(
                select(Product.id).where(Product.id == data.product_id).limit(1)
            )
            if product_id is None:
                return None

            item = CareItem(
                id=uuid4(),
                user_id=data.user_id,
                product_id=data.product_id,
                purchase_date=data.purchase_date,
                intake_start_date=data.intake_start_date,
                total_quantity=data.total_quantity,
                dose_per_intake=data.dose_per_intake,
                intakes_per_day=data.intakes_per_day,
                created_at=data.created_at,
                updated_at=data.created_at,
            )
            self._session.add(item)
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise CareItemPersistenceError from exc

        return CareItemRecord(
            id=item.id,
            user_id=item.user_id,
            product_id=item.product_id,
            purchase_date=item.purchase_date,
            intake_start_date=item.intake_start_date,
            total_quantity=item.total_quantity,
            dose_per_intake=item.dose_per_intake,
            intakes_per_day=item.intakes_per_day,
            created_at=item.created_at,
        )
