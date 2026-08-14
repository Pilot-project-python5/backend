"""게시 의약품 목록·상세 읽기 저장소."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import Row, Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.curation.models import Product
from allyakkkuk.medication.models import MedicationDetail


class MedicationPersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class MedicationSummaryRecord:
    id: UUID
    sku: str
    brand: str
    name: str
    image_url: str
    unit_form: str
    units_per_package: Decimal
    permit_code: str
    classification: str
    active_ingredients: str


@dataclass(frozen=True, slots=True)
class MedicationDetailRecord(MedicationSummaryRecord):
    efficacy: str
    dosage_instructions: str
    precautions: str
    storage_instructions: str
    source_name: str
    source_url: str
    source_reviewed_on: date


@dataclass(frozen=True, slots=True)
class MedicationPageRecord:
    items: tuple[MedicationSummaryRecord, ...]
    total: int


class MedicationRepository(Protocol):
    def list_published(self, *, page: int, page_size: int) -> MedicationPageRecord: ...

    def get_published(self, product_id: UUID) -> MedicationDetailRecord | None: ...


class SQLAlchemyMedicationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_published(self, *, page: int, page_size: int) -> MedicationPageRecord:
        try:
            total = int(
                self._session.execute(
                    select(func.count())
                    .select_from(Product)
                    .join(
                        MedicationDetail,
                        MedicationDetail.product_id == Product.id,
                    )
                    .where(
                        Product.product_type == "MEDICATION",
                        Product.is_published.is_(True),
                    )
                ).scalar_one()
            )
            offset = (page - 1) * page_size
            if offset >= total:
                return MedicationPageRecord((), total)
            rows = tuple(
                self._session.execute(
                    self._summary_select()
                    .where(
                        Product.product_type == "MEDICATION",
                        Product.is_published.is_(True),
                    )
                    .order_by(Product.sort_order, Product.sku)
                    .offset(offset)
                    .limit(page_size)
                )
            )
        except SQLAlchemyError as exc:
            raise MedicationPersistenceError from exc
        return MedicationPageRecord(
            tuple(self._summary_from_row(row) for row in rows), total
        )

    def get_published(self, product_id: UUID) -> MedicationDetailRecord | None:
        try:
            row = self._session.execute(
                select(
                    Product.id,
                    Product.sku,
                    Product.brand,
                    Product.name,
                    Product.image_url,
                    Product.unit_form,
                    Product.units_per_package,
                    MedicationDetail.permit_code,
                    MedicationDetail.classification,
                    MedicationDetail.active_ingredients,
                    MedicationDetail.efficacy,
                    MedicationDetail.dosage_instructions,
                    MedicationDetail.precautions,
                    MedicationDetail.storage_instructions,
                    MedicationDetail.source_name,
                    MedicationDetail.source_url,
                    MedicationDetail.source_reviewed_on,
                )
                .join(
                    MedicationDetail,
                    MedicationDetail.product_id == Product.id,
                )
                .where(
                    Product.id == product_id,
                    Product.product_type == "MEDICATION",
                    Product.is_published.is_(True),
                )
            ).one_or_none()
        except SQLAlchemyError as exc:
            raise MedicationPersistenceError from exc
        if row is None:
            return None
        return MedicationDetailRecord(*row)

    @staticmethod
    def _summary_select() -> Select[Any]:
        return select(
            Product.id,
            Product.sku,
            Product.brand,
            Product.name,
            Product.image_url,
            Product.unit_form,
            Product.units_per_package,
            MedicationDetail.permit_code,
            MedicationDetail.classification,
            MedicationDetail.active_ingredients,
        ).join(
            MedicationDetail,
            MedicationDetail.product_id == Product.id,
        )

    @staticmethod
    def _summary_from_row(row: Row[Any]) -> MedicationSummaryRecord:
        return MedicationSummaryRecord(
            id=row.id,
            sku=row.sku,
            brand=row.brand,
            name=row.name,
            image_url=row.image_url,
            unit_form=row.unit_form,
            units_per_package=row.units_per_package,
            permit_code=row.permit_code,
            classification=row.classification,
            active_ingredients=row.active_ingredients,
        )
