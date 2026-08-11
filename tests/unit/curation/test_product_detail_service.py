from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

from allyakkkuk.core.errors import AppError
from allyakkkuk.curation.product_detail_repository import (
    NutrientRecord,
    ProductDetailPersistenceError,
    ProductDetailRecord,
    ProductDetailRepository,
)
from allyakkkuk.curation.product_detail_service import ProductDetailService

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-2.4")]

PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000001")


class FakeProductDetailRepository(ProductDetailRepository):
    def __init__(
        self,
        result: ProductDetailRecord | None = None,
        *,
        fails: bool = False,
    ) -> None:
        self.result = result
        self.fails = fails
        self.calls: list[UUID] = []

    def get_published(self, product_id: UUID) -> ProductDetailRecord | None:
        self.calls.append(product_id)
        if self.fails:
            raise ProductDetailPersistenceError
        return self.result


def detail_record() -> ProductDetailRecord:
    return ProductDetailRecord(
        id=PRODUCT_ID,
        sku="LIFE-TWO-PER-DAY",
        product_type="SUPPLEMENT",
        brand="Life Extension",
        name="라이프익스텐션 투퍼데이",
        image_url="/static/products/life-extension-two-per-day.svg",
        display_price=28400,
        category_slugs=("vitamin",),
        unit_form="TABLET",
        units_per_package=Decimal("120.00"),
        nutrients=(
            NutrientRecord(
                code="VITAMIN_C",
                name="비타민 C",
                amount_per_unit=Decimal("235.0000"),
                unit="MG",
            ),
        ),
    )


def test_get_product_returns_package_and_nutrients() -> None:
    repository = FakeProductDetailRepository(detail_record())

    result = ProductDetailService(repository).get_product(PRODUCT_ID)

    assert result.id == PRODUCT_ID
    assert result.units_per_package == Decimal("120.00")
    assert result.category_slugs == ("vitamin",)
    assert result.nutrients[0].code == "VITAMIN_C"
    assert result.nutrients[0].amount_per_unit == Decimal("235.0000")
    assert repository.calls == [PRODUCT_ID]


def test_get_product_maps_ineligible_product_to_not_found() -> None:
    service = ProductDetailService(FakeProductDetailRepository())

    with pytest.raises(AppError) as captured:
        service.get_product(PRODUCT_ID)

    assert captured.value.status_code == 404
    assert captured.value.code == "PRODUCT_NOT_FOUND"
    assert captured.value.message == "제품을 찾을 수 없습니다."


def test_get_product_maps_database_failure_to_service_unavailable() -> None:
    service = ProductDetailService(FakeProductDetailRepository(fails=True))

    with pytest.raises(AppError) as captured:
        service.get_product(PRODUCT_ID)

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"
    assert captured.value.message == "서비스가 아직 준비되지 않았습니다."
