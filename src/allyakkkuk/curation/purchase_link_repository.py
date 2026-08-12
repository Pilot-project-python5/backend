"""공개 제품 외부 구매 링크 저장소."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.curation.models import (
    Product,
    ProductCategory,
    ProductCategoryMapping,
    PurchaseLink,
)


class PurchaseLinkPersistenceError(Exception):
    """구매 링크 조회 실패."""


@dataclass(frozen=True, slots=True)
class PurchaseLinkRecord:
    product_exists: bool
    url: str | None


class PurchaseLinkRepository(Protocol):
    def get_first_for_public_product(
        self, product_id: UUID
    ) -> PurchaseLinkRecord | None: ...


class SQLAlchemyPurchaseLinkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_first_for_public_product(
        self, product_id: UUID
    ) -> PurchaseLinkRecord | None:
        active_category = (
            select(ProductCategoryMapping.product_id)
            .join(
                ProductCategory,
                ProductCategory.id == ProductCategoryMapping.category_id,
            )
            .where(
                ProductCategoryMapping.product_id == Product.id,
                ProductCategory.is_active.is_(True),
            )
        )
        try:
            public_product_id = self._session.execute(
                select(Product.id).where(
                    Product.id == product_id,
                    Product.is_published.is_(True),
                    exists(active_category),
                )
            ).scalar_one_or_none()
            if public_product_id is None:
                return None

            url = self._session.execute(
                select(PurchaseLink.url)
                .where(
                    PurchaseLink.product_id == public_product_id,
                    PurchaseLink.is_active.is_(True),
                )
                .order_by(PurchaseLink.sort_order, PurchaseLink.id)
                .limit(1)
            ).scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise PurchaseLinkPersistenceError from exc

        return PurchaseLinkRecord(product_exists=True, url=url)
