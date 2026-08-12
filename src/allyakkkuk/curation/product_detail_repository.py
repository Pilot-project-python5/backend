"""공개 추천 제품 상세 읽기 저장소."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.curation.models import (
    ExpertComment,
    Nutrient,
    Product,
    ProductCategory,
    ProductCategoryMapping,
    ProductNutrient,
)


class ProductDetailPersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class NutrientRecord:
    code: str
    name: str
    amount_per_unit: Decimal
    unit: str


@dataclass(frozen=True, slots=True)
class ExpertCommentRecord:
    id: UUID
    author_label: str
    content: str


@dataclass(frozen=True, slots=True)
class ProductDetailRecord:
    id: UUID
    sku: str
    product_type: str
    brand: str
    name: str
    image_url: str
    display_price: int
    category_slugs: tuple[str, ...]
    unit_form: str
    units_per_package: Decimal
    nutrients: tuple[NutrientRecord, ...]
    expert_comments: tuple[ExpertCommentRecord, ...] = ()


class ProductDetailRepository(Protocol):
    def get_published(self, product_id: UUID) -> ProductDetailRecord | None: ...


class SQLAlchemyProductDetailRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_published(self, product_id: UUID) -> ProductDetailRecord | None:
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
            product = self._session.execute(
                select(Product).where(
                    Product.id == product_id,
                    Product.is_published.is_(True),
                    exists(active_category),
                )
            ).scalar_one_or_none()
            if product is None:
                return None

            category_slugs = tuple(
                self._session.execute(
                    select(ProductCategory.slug)
                    .join(
                        ProductCategoryMapping,
                        ProductCategoryMapping.category_id == ProductCategory.id,
                    )
                    .where(
                        ProductCategoryMapping.product_id == product.id,
                        ProductCategory.is_active.is_(True),
                    )
                    .order_by(ProductCategory.sort_order, ProductCategory.slug)
                ).scalars()
            )
            nutrient_rows = tuple(
                self._session.execute(
                    select(
                        Nutrient.code,
                        Nutrient.name,
                        ProductNutrient.amount_per_unit,
                        ProductNutrient.unit,
                    )
                    .join(
                        ProductNutrient,
                        ProductNutrient.nutrient_id == Nutrient.id,
                    )
                    .where(
                        ProductNutrient.product_id == product.id,
                        Nutrient.is_active.is_(True),
                    )
                    .order_by(ProductNutrient.sort_order, Nutrient.code)
                )
            )
            expert_comment_rows = tuple(
                self._session.execute(
                    select(
                        ExpertComment.id,
                        ExpertComment.author_label,
                        ExpertComment.content,
                    )
                    .where(
                        ExpertComment.product_id == product.id,
                        ExpertComment.is_active.is_(True),
                    )
                    .order_by(ExpertComment.sort_order, ExpertComment.id)
                )
            )
        except SQLAlchemyError as exc:
            raise ProductDetailPersistenceError from exc

        return ProductDetailRecord(
            id=product.id,
            sku=product.sku,
            product_type=product.product_type,
            brand=product.brand,
            name=product.name,
            image_url=product.image_url,
            display_price=product.display_price,
            category_slugs=category_slugs,
            unit_form=product.unit_form,
            units_per_package=product.units_per_package,
            nutrients=tuple(
                NutrientRecord(
                    code=code,
                    name=name,
                    amount_per_unit=amount_per_unit,
                    unit=unit,
                )
                for code, name, amount_per_unit, unit in nutrient_rows
            ),
            expert_comments=tuple(
                ExpertCommentRecord(
                    id=comment_id,
                    author_label=author_label,
                    content=content,
                )
                for comment_id, author_label, content in expert_comment_rows
            ),
        )
