from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from yeongyangkkuk.core.config import Settings
from yeongyangkkuk.curation.product_detail_router import get_product_detail_service
from yeongyangkkuk.curation.product_detail_service import (
    ExpertComment,
    ProductDetail,
    ProductDetailService,
)
from yeongyangkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-2.4.1")]

PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000001")
COMMENT_ID = UUID("24000000-0000-4000-8000-000000000001")


class StubExpertCommentService:
    def get_product(self, product_id: UUID) -> ProductDetail:
        return ProductDetail(
            id=product_id,
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
                ExpertComment(
                    id=COMMENT_ID,
                    author_label="MJ's COMMENT",
                    content="<script>문자열 그대로 전달</script>",
                ),
            ),
        )


class StubEmptyExpertCommentService(StubExpertCommentService):
    def get_product(self, product_id: UUID) -> ProductDetail:
        return replace(super().get_product(product_id), expert_comments=())


def contract_client(service: object) -> TestClient:
    application = create_app(Settings(app_env="test"))
    application.dependency_overrides[get_product_detail_service] = lambda: cast(
        ProductDetailService, service
    )
    return TestClient(application)


def test_product_detail_returns_expert_comment_plain_string_contract() -> None:
    with contract_client(StubExpertCommentService()) as client:
        response = client.get(f"/api/v1/curation/products/{PRODUCT_ID}")

    assert response.status_code == 200
    assert response.json()["expert_comments"] == [
        {
            "id": str(COMMENT_ID),
            "author_label": "MJ's COMMENT",
            "content": "<script>문자열 그대로 전달</script>",
        }
    ]


def test_product_detail_returns_empty_expert_comments() -> None:
    with contract_client(StubEmptyExpertCommentService()) as client:
        response = client.get(f"/api/v1/curation/products/{PRODUCT_ID}")

    assert response.status_code == 200
    assert response.json()["expert_comments"] == []


def test_openapi_requires_expert_comments_on_product_detail() -> None:
    schema = create_app(Settings(app_env="test")).openapi()
    detail = schema["components"]["schemas"]["ProductDetailResponse"]
    comment = schema["components"]["schemas"]["ExpertCommentResponse"]

    assert "expert_comments" in detail["required"]
    assert detail["properties"]["expert_comments"]["items"]["$ref"].endswith(
        "/ExpertCommentResponse"
    )
    assert set(comment["required"]) == {"id", "author_label", "content"}
