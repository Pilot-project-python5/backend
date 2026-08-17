from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

from yeongyangkkuk.curation.product_detail_repository import (
    ExpertCommentRecord,
    ProductDetailRecord,
    ProductDetailRepository,
)
from yeongyangkkuk.curation.product_detail_service import ProductDetailService

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-2.4.1")]

PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000001")
COMMENT_ID = UUID("24000000-0000-4000-8000-000000000001")


class FakeProductDetailRepository(ProductDetailRepository):
    def __init__(self, result: ProductDetailRecord) -> None:
        self.result = result

    def get_published(self, product_id: UUID) -> ProductDetailRecord | None:
        return self.result


def test_get_product_maps_expert_comments() -> None:
    repository = FakeProductDetailRepository(
        ProductDetailRecord(
            id=PRODUCT_ID,
            sku="LIFE-TWO-PER-DAY",
            product_type="SUPPLEMENT",
            brand="Life Extension",
            name="라이프익스텐션 투퍼데이",
            image_url="/static/products/life-extension-two-per-day.svg",
            display_price=28400,
            category_slugs=("vitamin",),
            unit_form="TABLET",
            units_per_package=Decimal("120"),
            nutrients=(),
            expert_comments=(
                ExpertCommentRecord(
                    id=COMMENT_ID,
                    author_label="MJ's COMMENT",
                    content="개발용 전문가 코멘트",
                ),
            ),
        )
    )

    result = ProductDetailService(repository).get_product(PRODUCT_ID)

    assert [
        (item.id, item.author_label, item.content) for item in result.expert_comments
    ] == [(COMMENT_ID, "MJ's COMMENT", "개발용 전문가 코멘트")]
