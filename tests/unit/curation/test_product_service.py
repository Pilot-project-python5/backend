from __future__ import annotations

from uuid import UUID

import pytest

from allyakkkuk.core.errors import AppError
from allyakkkuk.curation.product_repository import (
    ProductPageRecord,
    ProductPersistenceError,
    ProductRecord,
    ProductRepository,
)
from allyakkkuk.curation.product_service import ProductService

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-2.3")]


class FakeProductRepository(ProductRepository):
    def __init__(
        self,
        *,
        active_categories: set[str] | None = None,
        page: ProductPageRecord | None = None,
        fail_on: str | None = None,
    ) -> None:
        self.active_categories = active_categories or set()
        self.page = page or ProductPageRecord(items=(), total=0)
        self.fail_on = fail_on
        self.list_calls: list[tuple[str | None, int, int]] = []

    def category_is_active(self, slug: str) -> bool:
        if self.fail_on == "category":
            raise ProductPersistenceError
        return slug in self.active_categories

    def list_published(
        self,
        *,
        category_slug: str | None,
        page: int,
        page_size: int,
    ) -> ProductPageRecord:
        if self.fail_on == "list":
            raise ProductPersistenceError
        self.list_calls.append((category_slug, page, page_size))
        return self.page


def product(value: int = 1) -> ProductRecord:
    return ProductRecord(
        id=UUID(f"22000000-0000-4000-8000-{value:012d}"),
        sku=f"PRODUCT-{value}",
        product_type="SUPPLEMENT",
        brand="샘플 브랜드",
        name=f"샘플 제품 {value}",
        image_url=f"/static/products/product-{value}.svg",
        display_price=1000 * value,
        category_slugs=("vitamin",),
    )


def test_list_products_uses_all_as_no_category_filter_and_builds_page() -> None:
    repository = FakeProductRepository(
        page=ProductPageRecord(items=(product(1), product(2)), total=3)
    )

    result = ProductService(repository).list_products(
        category="all",
        page=1,
        page_size=2,
    )

    assert [item.sku for item in result.items] == ["PRODUCT-1", "PRODUCT-2"]
    assert result.page == 1
    assert result.page_size == 2
    assert result.total == 3
    assert result.has_next is True
    assert repository.list_calls == [(None, 1, 2)]


def test_list_products_validates_real_category_before_querying() -> None:
    repository = FakeProductRepository(active_categories={"vitamin"})

    result = ProductService(repository).list_products(
        category="vitamin",
        page=2,
        page_size=20,
    )

    assert result.items == ()
    assert result.has_next is False
    assert repository.list_calls == [("vitamin", 2, 20)]


def test_list_products_rejects_unknown_or_inactive_category() -> None:
    service = ProductService(FakeProductRepository())

    with pytest.raises(AppError) as captured:
        service.list_products(category="unknown", page=1, page_size=20)

    assert captured.value.status_code == 404
    assert captured.value.code == "CATEGORY_NOT_FOUND"


@pytest.mark.parametrize("fail_on", ["category", "list"])
def test_list_products_maps_database_failures_to_503(fail_on: str) -> None:
    service = ProductService(
        FakeProductRepository(active_categories={"vitamin"}, fail_on=fail_on)
    )

    with pytest.raises(AppError) as captured:
        service.list_products(category="vitamin", page=1, page_size=20)

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"
    assert captured.value.message == "서비스가 아직 준비되지 않았습니다."
