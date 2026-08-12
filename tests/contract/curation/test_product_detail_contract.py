from __future__ import annotations

from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from allyakkkuk.core.config import Settings
from allyakkkuk.core.errors import AppError
from allyakkkuk.curation.product_detail_router import get_product_detail_service
from allyakkkuk.curation.product_detail_service import (
    NutrientAmount,
    ProductDetail,
    ProductDetailService,
)
from allyakkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-2.4")]

PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000001")


class StubProductDetailService:
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
            units_per_package=Decimal("120.00"),
            nutrients=(
                NutrientAmount(
                    code="VITAMIN_C",
                    name="비타민 C",
                    amount_per_unit=Decimal("235.0000"),
                    unit="MG",
                ),
            ),
        )


class ErrorProductDetailService:
    def __init__(self, error: AppError) -> None:
        self.error = error

    def get_product(self, product_id: UUID) -> ProductDetail:
        raise self.error


def contract_client(service: object) -> TestClient:
    application = create_app(Settings(app_env="test"))
    application.dependency_overrides[get_product_detail_service] = lambda: cast(
        ProductDetailService, service
    )
    return TestClient(application)


def test_product_detail_returns_public_package_and_nutrient_contract() -> None:
    with contract_client(StubProductDetailService()) as client:
        response = client.get(f"/api/v1/curation/products/{PRODUCT_ID}")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(PRODUCT_ID),
        "sku": "LIFE-TWO-PER-DAY",
        "product_type": "SUPPLEMENT",
        "brand": "Life Extension",
        "name": "라이프익스텐션 투퍼데이",
        "image_url": "/static/products/life-extension-two-per-day.svg",
        "display_price": 28400,
        "currency": "KRW",
        "category_slugs": ["vitamin"],
        "package": {
            "unit_form": "TABLET",
            "units_per_package": "120",
        },
        "nutrients": [
            {
                "code": "VITAMIN_C",
                "name": "비타민 C",
                "amount_per_unit": "235",
                "unit": "MG",
            }
        ],
        "expert_comments": [],
    }


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (
            AppError(
                status_code=404,
                code="PRODUCT_NOT_FOUND",
                message="제품을 찾을 수 없습니다.",
            ),
            404,
            "PRODUCT_NOT_FOUND",
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
def test_product_detail_uses_common_error_contract(
    error: AppError,
    status_code: int,
    code: str,
) -> None:
    with contract_client(ErrorProductDetailService(error)) as client:
        response = client.get(f"/api/v1/curation/products/{PRODUCT_ID}")

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code


def test_product_detail_rejects_invalid_uuid_contract() -> None:
    with contract_client(StubProductDetailService()) as client:
        response = client.get("/api/v1/curation/products/not-a-uuid")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_openapi_documents_public_product_detail_and_responses() -> None:
    schema = create_app(Settings(app_env="test")).openapi()
    operation = schema["paths"]["/api/v1/curation/products/{product_id}"]["get"]
    parameter = operation["parameters"][0]

    assert operation["operationId"] == "curation_get_recommended_product"
    assert operation.get("security", []) == []
    assert parameter["name"] == "product_id"
    assert parameter["schema"]["format"] == "uuid"
    assert set(operation["responses"]) >= {"200", "404", "422", "503"}
