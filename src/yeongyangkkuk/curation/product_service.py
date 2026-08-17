"""공개 추천 제품 목록 애플리케이션 서비스."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.curation.product_repository import (
    ProductPersistenceError,
    ProductRepository,
)


@dataclass(frozen=True, slots=True)
class ProductListItem:
    id: UUID
    sku: str
    product_type: str
    brand: str
    name: str
    image_url: str
    display_price: int
    category_slugs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProductListResult:
    items: tuple[ProductListItem, ...]
    page: int
    page_size: int
    total: int
    has_next: bool


class ProductService:
    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    def list_products(
        self,
        *,
        category: str,
        page: int,
        page_size: int,
    ) -> ProductListResult:
        category_slug = None if category == "all" else category
        try:
            if category_slug is not None and not self._repository.category_is_active(
                category_slug
            ):
                raise AppError(
                    status_code=404,
                    code="CATEGORY_NOT_FOUND",
                    message="카테고리를 찾을 수 없습니다.",
                )
            result = self._repository.list_published(
                category_slug=category_slug,
                page=page,
                page_size=page_size,
            )
        except ProductPersistenceError as exc:
            raise AppError(
                status_code=503,
                code="SERVICE_UNAVAILABLE",
                message="서비스가 아직 준비되지 않았습니다.",
            ) from exc

        return ProductListResult(
            items=tuple(
                ProductListItem(
                    id=item.id,
                    sku=item.sku,
                    product_type=item.product_type,
                    brand=item.brand,
                    name=item.name,
                    image_url=item.image_url,
                    display_price=item.display_price,
                    category_slugs=item.category_slugs,
                )
                for item in result.items
            ),
            page=page,
            page_size=page_size,
            total=result.total,
            has_next=page * page_size < result.total,
        )
