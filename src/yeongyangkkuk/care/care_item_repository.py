"""복용 제품 등록 저장소 포트와 PostgreSQL 구현."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from yeongyangkkuk.care.models import CareItem, CareNutrientSnapshot
from yeongyangkkuk.curation.models import Nutrient, Product, ProductNutrient


class CareItemPersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class CareItemCreateData:
    user_id: UUID
    product_id: UUID
    purchase_date: date
    intake_start_date: date
    expected_depletion_date: date
    total_quantity: Decimal
    dose_per_intake: Decimal
    intakes_per_day: int
    created_at: datetime
    expiration_date: date | None = None


@dataclass(frozen=True, slots=True)
class CareItemRecord:
    id: UUID
    user_id: UUID
    product_id: UUID
    purchase_date: date
    intake_start_date: date
    expected_depletion_date: date
    total_quantity: Decimal
    quantity_unit: str
    dose_per_intake: Decimal
    intakes_per_day: int
    created_at: datetime
    expiration_date: date | None = None


@dataclass(frozen=True, slots=True)
class CareItemListRecord:
    id: UUID
    product_id: UUID
    product_type: str
    brand: str
    name: str
    image_url: str
    purchase_date: date
    intake_start_date: date
    expected_depletion_date: date
    total_quantity: Decimal
    quantity_unit: str
    dose_per_intake: Decimal
    intakes_per_day: int
    created_at: datetime
    expiration_date: date | None = None


@dataclass(frozen=True, slots=True)
class CareItemPageRecord:
    items: tuple[CareItemListRecord, ...]
    total: int


@dataclass(frozen=True, slots=True)
class NutrientSnapshotSource:
    nutrient_id: UUID
    nutrient_name: str
    amount_per_unit: Decimal
    unit: str


def build_nutrient_snapshots(
    care_item_id: UUID,
    sources: tuple[NutrientSnapshotSource, ...],
) -> tuple[CareNutrientSnapshot, ...]:
    """카탈로그 조회 결과를 변경 불가능한 등록 시점 값으로 복사한다."""

    return tuple(
        CareNutrientSnapshot(
            id=uuid4(),
            care_item_id=care_item_id,
            nutrient_id=source.nutrient_id,
            nutrient_name=source.nutrient_name,
            amount_per_unit=source.amount_per_unit,
            unit=source.unit,
        )
        for source in sources
    )


class CareItemRepository(Protocol):
    def create(self, data: CareItemCreateData) -> CareItemRecord | None: ...


class CareItemManagementRepository(Protocol):
    def list_active(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
    ) -> CareItemPageRecord: ...

    def soft_delete(
        self,
        *,
        user_id: UUID,
        care_item_id: UUID,
        deleted_at: datetime,
    ) -> bool: ...

    def update_expiration(
        self,
        *,
        user_id: UUID,
        care_item_id: UUID,
        expiration_date: date,
        updated_at: datetime,
    ) -> bool: ...


class SQLAlchemyCareItemRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, data: CareItemCreateData) -> CareItemRecord | None:
        try:
            product = self._session.execute(
                select(Product.id, Product.product_type, Product.unit_form)
                .where(Product.id == data.product_id)
                .limit(1)
            ).one_or_none()
            if product is None:
                return None

            snapshot_sources: tuple[NutrientSnapshotSource, ...] = ()
            if product.product_type == "SUPPLEMENT":
                rows = self._session.execute(
                    select(
                        Nutrient.id,
                        Nutrient.name,
                        ProductNutrient.amount_per_unit,
                        ProductNutrient.unit,
                    )
                    .join(
                        ProductNutrient,
                        ProductNutrient.nutrient_id == Nutrient.id,
                    )
                    .where(
                        ProductNutrient.product_id == data.product_id,
                        Nutrient.is_active.is_(True),
                    )
                    .order_by(ProductNutrient.sort_order, Nutrient.code)
                )
                snapshot_sources = tuple(
                    NutrientSnapshotSource(
                        nutrient_id=row.id,
                        nutrient_name=row.name,
                        amount_per_unit=row.amount_per_unit,
                        unit=row.unit,
                    )
                    for row in rows
                )

            item_id = uuid4()
            item = CareItem(
                id=item_id,
                user_id=data.user_id,
                product_id=data.product_id,
                purchase_date=data.purchase_date,
                intake_start_date=data.intake_start_date,
                expected_depletion_date=data.expected_depletion_date,
                expiration_date=data.expiration_date,
                total_quantity=data.total_quantity,
                quantity_unit=product.unit_form,
                dose_per_intake=data.dose_per_intake,
                intakes_per_day=data.intakes_per_day,
                created_at=data.created_at,
                updated_at=data.created_at,
            )
            self._session.add(item)
            self._session.add_all(build_nutrient_snapshots(item_id, snapshot_sources))
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
            expected_depletion_date=item.expected_depletion_date,
            total_quantity=item.total_quantity,
            quantity_unit=item.quantity_unit,
            dose_per_intake=item.dose_per_intake,
            intakes_per_day=item.intakes_per_day,
            created_at=item.created_at,
            expiration_date=item.expiration_date,
        )

    def list_active(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
    ) -> CareItemPageRecord:
        try:
            filters = (
                CareItem.user_id == user_id,
                CareItem.deleted_at.is_(None),
            )
            total = self._session.scalar(
                select(func.count()).select_from(CareItem).where(*filters)
            )
            resolved_total = int(total or 0)
            offset = (page - 1) * page_size
            if offset >= resolved_total:
                return CareItemPageRecord(items=(), total=resolved_total)

            rows = self._session.execute(
                select(CareItem, Product)
                .join(Product, Product.id == CareItem.product_id)
                .where(*filters)
                .order_by(CareItem.created_at.desc(), CareItem.id.desc())
                .offset(offset)
                .limit(page_size)
            )
            items = tuple(
                CareItemListRecord(
                    id=item.id,
                    product_id=item.product_id,
                    product_type=product.product_type,
                    brand=product.brand,
                    name=product.name,
                    image_url=product.image_url,
                    purchase_date=item.purchase_date,
                    intake_start_date=item.intake_start_date,
                    expected_depletion_date=item.expected_depletion_date,
                    expiration_date=item.expiration_date,
                    total_quantity=item.total_quantity,
                    quantity_unit=item.quantity_unit,
                    dose_per_intake=item.dose_per_intake,
                    intakes_per_day=item.intakes_per_day,
                    created_at=item.created_at,
                )
                for item, product in rows
            )
        except SQLAlchemyError as exc:
            raise CareItemPersistenceError from exc

        return CareItemPageRecord(items=items, total=resolved_total)

    def update_expiration(
        self,
        *,
        user_id: UUID,
        care_item_id: UUID,
        expiration_date: date,
        updated_at: datetime,
    ) -> bool:
        try:
            updated_id = self._session.scalar(
                update(CareItem)
                .where(
                    CareItem.id == care_item_id,
                    CareItem.user_id == user_id,
                    CareItem.deleted_at.is_(None),
                )
                .values(
                    expiration_date=expiration_date,
                    updated_at=updated_at,
                )
                .returning(CareItem.id)
            )
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise CareItemPersistenceError from exc
        return updated_id is not None

    def soft_delete(
        self,
        *,
        user_id: UUID,
        care_item_id: UUID,
        deleted_at: datetime,
    ) -> bool:
        try:
            deleted_id = self._session.scalar(
                update(CareItem)
                .where(
                    CareItem.id == care_item_id,
                    CareItem.user_id == user_id,
                    CareItem.deleted_at.is_(None),
                )
                .values(deleted_at=deleted_at, updated_at=deleted_at)
                .returning(CareItem.id)
            )
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise CareItemPersistenceError from exc

        return deleted_id is not None
