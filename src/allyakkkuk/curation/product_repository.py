"""게시 추천 제품 목록 읽기 저장소."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.curation.models import (
    Product,
    ProductCategory,
    ProductCategoryMapping,
)


class ProductPersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ProductRecord:
    id: UUID
    sku: str
    product_type: str
    brand: str
    name: str
    image_url: str
    display_price: int
    category_slugs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProductPageRecord:
    items: tuple[ProductRecord, ...]
    total: int


class ProductRepository(Protocol):
    def category_is_active(self, slug: str) -> bool: ...

    def list_published(
        self,
        *,
        category_slug: str | None,
        page: int,
        page_size: int,
    ) -> ProductPageRecord: ...


class SQLAlchemyProductRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def category_is_active(self, slug: str) -> bool:
        try:
            result = self._session.scalar(
                select(
                    exists().where(
                        ProductCategory.slug == slug,
                        ProductCategory.is_active.is_(True),
                    )
                )
            )
            return bool(result)
        except SQLAlchemyError as exc:
            raise ProductPersistenceError from exc

    def list_published(
        self,
        *,
        category_slug: str | None,
        page: int,
        page_size: int,
    ) -> ProductPageRecord:
        active_mapping = (
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
        if category_slug is not None:
            active_mapping = active_mapping.where(ProductCategory.slug == category_slug)
        eligible = Product.is_published.is_(True) & exists(active_mapping)

        try:
            total = int(
                self._session.scalar(
                    select(func.count()).select_from(Product).where(eligible)
                )
                or 0
            )
            offset = (page - 1) * page_size
            if offset >= total:
                return ProductPageRecord(items=(), total=total)

            products = tuple(
                self._session.execute(
                    select(Product)
                    .where(eligible)
                    .order_by(Product.sort_order, Product.sku)
                    .offset(offset)
                    .limit(page_size)
                ).scalars()
            )
            product_ids = tuple(item.id for item in products)
            category_rows = tuple(
                self._session.execute(
                    select(
                        ProductCategoryMapping.product_id,
                        ProductCategory.slug,
                    )
                    .join(
                        ProductCategory,
                        ProductCategory.id == ProductCategoryMapping.category_id,
                    )
                    .where(
                        ProductCategoryMapping.product_id.in_(product_ids),
                        ProductCategory.is_active.is_(True),
                    )
                    .order_by(
                        ProductCategoryMapping.product_id,
                        ProductCategory.sort_order,
                        ProductCategory.slug,
                    )
                )
            )
        except SQLAlchemyError as exc:
            raise ProductPersistenceError from exc

        slugs_by_product: dict[UUID, list[str]] = {
            product_id: [] for product_id in product_ids
        }
        for product_id, slug in category_rows:
            slugs_by_product[product_id].append(slug)

        return ProductPageRecord(
            items=tuple(
                ProductRecord(
                    id=item.id,
                    sku=item.sku,
                    product_type=item.product_type,
                    brand=item.brand,
                    name=item.name,
                    image_url=item.image_url,
                    display_price=item.display_price,
                    category_slugs=tuple(slugs_by_product[item.id]),
                )
                for item in products
            ),
            total=total,
        )
