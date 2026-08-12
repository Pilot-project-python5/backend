from __future__ import annotations

from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from allyakkkuk.core.config import Settings
from allyakkkuk.core.errors import AppError
from allyakkkuk.curation.purchase_link_router import get_purchase_link_service
from allyakkkuk.curation.purchase_link_service import PurchaseLinkService
from allyakkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-2.4.2")]

PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000001")
DESTINATION = "https://example.com/allyakkkuk/products/life-two-per-day"


class StubPurchaseLinkService:
    def get_destination(self, product_id: UUID) -> str:
        return DESTINATION


class ErrorPurchaseLinkService:
    def __init__(self, error: AppError) -> None:
        self.error = error

    def get_destination(self, product_id: UUID) -> str:
        raise self.error


def contract_client(service: object) -> TestClient:
    application = create_app(Settings(app_env="test"))
    application.dependency_overrides[get_purchase_link_service] = lambda: cast(
        PurchaseLinkService, service
    )
    return TestClient(application)


def test_purchase_redirect_contract_has_location_and_security_headers() -> None:
    with contract_client(StubPurchaseLinkService()) as client:
        response = client.get(
            f"/api/v1/curation/products/{PRODUCT_ID}/purchase",
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert response.headers["location"] == DESTINATION
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.content == b""


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (
            AppError(
                status_code=404,
                code="PRODUCT_NOT_FOUND",
                message="제품을 찾을 수 없습니다.",
            ),
            "PRODUCT_NOT_FOUND",
        ),
        (
            AppError(
                status_code=404,
                code="PURCHASE_LINK_NOT_FOUND",
                message="구매 링크를 찾을 수 없습니다.",
            ),
            "PURCHASE_LINK_NOT_FOUND",
        ),
        (
            AppError(
                status_code=503,
                code="SERVICE_UNAVAILABLE",
                message="서비스가 아직 준비되지 않았습니다.",
            ),
            "SERVICE_UNAVAILABLE",
        ),
    ],
)
def test_purchase_redirect_uses_common_error_contract(
    error: AppError,
    code: str,
) -> None:
    with contract_client(ErrorPurchaseLinkService(error)) as client:
        response = client.get(
            f"/api/v1/curation/products/{PRODUCT_ID}/purchase",
            follow_redirects=False,
        )

    assert response.status_code == error.status_code
    assert response.json()["error"]["code"] == code


def test_purchase_redirect_rejects_invalid_uuid_contract() -> None:
    with contract_client(StubPurchaseLinkService()) as client:
        response = client.get(
            "/api/v1/curation/products/not-a-uuid/purchase",
            follow_redirects=False,
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_openapi_documents_purchase_redirect_and_responses() -> None:
    schema = create_app(Settings(app_env="test")).openapi()
    operation = schema["paths"]["/api/v1/curation/products/{product_id}/purchase"][
        "get"
    ]

    assert operation["operationId"] == "curation_redirect_to_purchase"
    assert operation.get("security", []) == []
    assert set(operation["responses"]) >= {"307", "404", "422", "503"}
    assert "200" not in operation["responses"]
    examples = operation["responses"]["404"]["content"]["application/json"]["examples"]
    assert set(examples) == {"product_not_found", "purchase_link_not_found"}
