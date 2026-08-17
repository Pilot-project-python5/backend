"""공개 추천 제품 상세 애플리케이션 서비스."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.curation.product_detail_repository import (
    ProductDetailPersistenceError,
    ProductDetailRepository,
)


@dataclass(frozen=True, slots=True)
class NutrientAmount:
    code: str
    name: str
    amount_per_unit: Decimal
    unit: str


@dataclass(frozen=True, slots=True)
class ExpertComment:
    id: UUID
    author_label: str
    content: str


@dataclass(frozen=True, slots=True)
class ProductDetail:
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
    nutrients: tuple[NutrientAmount, ...]
    expert_comments: tuple[ExpertComment, ...] = ()


class ProductDetailService:
    def __init__(self, repository: ProductDetailRepository) -> None:
        self._repository = repository

    def get_product(self, product_id: UUID) -> ProductDetail:
        try:
            result = self._repository.get_published(product_id)
        except ProductDetailPersistenceError as exc:
            raise AppError(
                status_code=503,
                code="SERVICE_UNAVAILABLE",
                message="서비스가 아직 준비되지 않았습니다.",
            ) from exc

        if result is None:
            raise AppError(
                status_code=404,
                code="PRODUCT_NOT_FOUND",
                message="제품을 찾을 수 없습니다.",
            )

        return ProductDetail(
            id=result.id,
            sku=result.sku,
            product_type=result.product_type,
            brand=result.brand,
            name=result.name,
            image_url=result.image_url,
            display_price=result.display_price,
            category_slugs=result.category_slugs,
            unit_form=result.unit_form,
            units_per_package=result.units_per_package,
            nutrients=tuple(
                NutrientAmount(
                    code=item.code,
                    name=item.name,
                    amount_per_unit=item.amount_per_unit,
                    unit=item.unit,
                )
                for item in result.nutrients
            ),
            expert_comments=tuple(
                ExpertComment(
                    id=item.id,
                    author_label=item.author_label,
                    content=item.content,
                )
                for item in result.expert_comments
            ),
        )
