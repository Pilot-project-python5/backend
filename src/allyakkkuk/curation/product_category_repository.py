"""활성 제품 카테고리 읽기 저장소."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.curation.models import ProductCategory


class ProductCategoryPersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ProductCategoryRecord:
    slug: str
    name: str
    sort_order: int


class ProductCategoryRepository(Protocol):
    def list_active(self) -> tuple[ProductCategoryRecord, ...]: ...


class SQLAlchemyProductCategoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_active(self) -> tuple[ProductCategoryRecord, ...]:
        try:
            categories = self._session.execute(
                select(ProductCategory)
                .where(
                    ProductCategory.is_active.is_(True),
                    ProductCategory.slug != "all",
                )
                .order_by(ProductCategory.sort_order, ProductCategory.slug)
            ).scalars()
            return tuple(
                ProductCategoryRecord(
                    slug=category.slug,
                    name=category.name,
                    sort_order=category.sort_order,
                )
                for category in categories
            )
        except SQLAlchemyError as exc:
            raise ProductCategoryPersistenceError from exc
