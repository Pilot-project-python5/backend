from __future__ import annotations

from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from yeongyangkkuk.core.config import Settings
from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.curation.product_router import get_product_service
from yeongyangkkuk.curation.product_service import (
    ProductListItem,
    ProductListResult,
    ProductService,
)
from yeongyangkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-2.3")]


class StubProductService:
    def list_products(
        self,
        *,
        category: str,
        page: int,
        page_size: int,
    ) -> ProductListResult:
        return ProductListResult(
            items=(
                ProductListItem(
                    id=UUID("22000000-0000-4000-8000-000000000001"),
                    sku="LIFE-TWO-PER-DAY",
                    product_type="SUPPLEMENT",
                    brand="Life Extension",
                    name="라이프익스텐션 투퍼데이",
                    image_url="/static/products/life-extension-two-per-day.svg",
                    display_price=28400,
                    category_slugs=("vitamin",),
                ),
            ),
            page=page,
            page_size=page_size,
            total=1,
            has_next=False,
        )


class ErrorProductService:
    def __init__(self, error: AppError) -> None:
        self.error = error

    def list_products(
        self,
        *,
        category: str,
        page: int,
        page_size: int,
    ) -> ProductListResult:
        raise self.error


def contract_client(service: object) -> TestClient:
    application = create_app(Settings(app_env="test"))
    application.dependency_overrides[get_product_service] = lambda: cast(
        ProductService, service
    )
    return TestClient(application)


def test_product_list_returns_public_card_and_page_contract() -> None:
    with contract_client(StubProductService()) as client:
        response = client.get(
            "/api/v1/curation/products",
            params={"category": "vitamin", "page": 1, "page_size": 20},
        )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "22000000-0000-4000-8000-000000000001",
                "sku": "LIFE-TWO-PER-DAY",
                "product_type": "SUPPLEMENT",
                "brand": "Life Extension",
                "name": "라이프익스텐션 투퍼데이",
                "image_url": "/static/products/life-extension-two-per-day.svg",
                "display_price": 28400,
                "currency": "KRW",
                "category_slugs": ["vitamin"],
            }
        ],
        "page": 1,
        "page_size": 20,
        "total": 1,
        "has_next": False,
    }


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (
            AppError(
                status_code=404,
                code="CATEGORY_NOT_FOUND",
                message="카테고리를 찾을 수 없습니다.",
            ),
            404,
            "CATEGORY_NOT_FOUND",
        ),
        (
            AppError(
                status_code=503,
                code="SERVICE_UNAVAILABLE",
                message="서비스가 아직 준비되지 않았습니다.",
            ),
            503,
            "SERVICE_UNAVAILABLE",
        ),
    ],
)
def test_product_list_uses_common_error_contract(
    error: AppError,
    status_code: int,
    code: str,
) -> None:
    with contract_client(ErrorProductService(error)) as client:
        response = client.get("/api/v1/curation/products")

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code


@pytest.mark.parametrize(
    "params",
    [
        {"category": "INVALID_SLUG"},
        {"page": 0},
        {"page_size": 0},
        {"page_size": 101},
    ],
)
def test_product_list_rejects_invalid_query_contract(params: dict[str, object]) -> None:
    with contract_client(StubProductService()) as client:
        response = client.get("/api/v1/curation/products", params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_openapi_documents_public_product_list_query_and_responses() -> None:
    schema = create_app(Settings(app_env="test")).openapi()
    operation = schema["paths"]["/api/v1/curation/products"]["get"]
    parameters = {item["name"]: item for item in operation["parameters"]}

    assert operation["operationId"] == "curation_list_recommended_products"
    assert operation.get("security", []) == []
    assert parameters["category"]["schema"]["default"] == "all"
    assert parameters["page"]["schema"]["default"] == 1
    assert parameters["page_size"]["schema"]["default"] == 20
    assert set(operation["responses"]) >= {"200", "404", "422", "503"}
