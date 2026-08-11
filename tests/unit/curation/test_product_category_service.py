from __future__ import annotations

import pytest

from allyakkkuk.core.errors import AppError
from allyakkkuk.curation.product_category_repository import (
    ProductCategoryPersistenceError,
    ProductCategoryRecord,
    ProductCategoryRepository,
)
from allyakkkuk.curation.product_category_service import ProductCategoryService

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-2.2")]


class FakeProductCategoryRepository(ProductCategoryRepository):
    def __init__(
        self,
        records: tuple[ProductCategoryRecord, ...] = (),
        *,
        fail: bool = False,
    ) -> None:
        self.records = records
        self.fail = fail
        self.calls = 0

    def list_active(self) -> tuple[ProductCategoryRecord, ...]:
        self.calls += 1
        if self.fail:
            raise ProductCategoryPersistenceError
        return self.records


def test_list_categories_prepends_virtual_all_to_repository_order() -> None:
    repository = FakeProductCategoryRepository(
        (
            ProductCategoryRecord(slug="vitamin", name="비타민", sort_order=10),
            ProductCategoryRecord(slug="protein", name="단백질", sort_order=20),
        )
    )

    result = ProductCategoryService(repository).list_categories()

    assert [(item.slug, item.name) for item in result] == [
        ("all", "전체"),
        ("vitamin", "비타민"),
        ("protein", "단백질"),
    ]
    assert repository.calls == 1


def test_list_categories_returns_virtual_all_when_no_active_rows() -> None:
    result = ProductCategoryService(FakeProductCategoryRepository()).list_categories()

    assert [(item.slug, item.name) for item in result] == [("all", "전체")]


def test_list_categories_maps_database_failure_to_service_unavailable() -> None:
    service = ProductCategoryService(FakeProductCategoryRepository(fail=True))

    with pytest.raises(AppError) as captured:
        service.list_categories()

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"
    assert captured.value.message == "서비스가 아직 준비되지 않았습니다."
