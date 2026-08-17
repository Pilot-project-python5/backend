"""공개 제품 카테고리 목록 애플리케이션 서비스."""

from __future__ import annotations

from dataclasses import dataclass

from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.curation.product_category_repository import (
    ProductCategoryPersistenceError,
    ProductCategoryRepository,
)


@dataclass(frozen=True, slots=True)
class ProductCategoryItem:
    slug: str
    name: str


ALL_CATEGORY = ProductCategoryItem(slug="all", name="전체")


class ProductCategoryService:
    def __init__(self, repository: ProductCategoryRepository) -> None:
        self._repository = repository

    def list_categories(self) -> tuple[ProductCategoryItem, ...]:
        try:
            categories = self._repository.list_active()
        except ProductCategoryPersistenceError as exc:
            raise AppError(
                status_code=503,
                code="SERVICE_UNAVAILABLE",
                message="서비스가 아직 준비되지 않았습니다.",
            ) from exc
        return (
            ALL_CATEGORY,
            *(
                ProductCategoryItem(slug=category.slug, name=category.name)
                for category in categories
            ),
        )
