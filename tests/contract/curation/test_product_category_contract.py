from __future__ import annotations

from typing import cast

import pytest
from fastapi.testclient import TestClient

from allyakkkuk.core.config import Settings
from allyakkkuk.core.errors import AppError
from allyakkkuk.curation.product_category_router import get_product_category_service
from allyakkkuk.curation.product_category_service import (
    ProductCategoryItem,
    ProductCategoryService,
)
from allyakkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-2.2")]


class StubProductCategoryService:
    def list_categories(self) -> tuple[ProductCategoryItem, ...]:
        return (
            ProductCategoryItem(slug="all", name="전체"),
            ProductCategoryItem(slug="vitamin", name="비타민"),
            ProductCategoryItem(slug="protein", name="단백질"),
            ProductCategoryItem(slug="omega-3", name="오메가3"),
        )


class UnavailableProductCategoryService:
    def list_categories(self) -> tuple[ProductCategoryItem, ...]:
        raise AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="서비스가 아직 준비되지 않았습니다.",
        )


def contract_client(service: object) -> TestClient:
    application = create_app(Settings(app_env="test"))
    application.dependency_overrides[get_product_category_service] = lambda: cast(
        ProductCategoryService, service
    )
    return TestClient(application)


def test_categories_returns_public_slug_name_contract() -> None:
    with contract_client(StubProductCategoryService()) as client:
        response = client.get("/api/v1/curation/categories")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"slug": "all", "name": "전체"},
            {"slug": "vitamin", "name": "비타민"},
            {"slug": "protein", "name": "단백질"},
            {"slug": "omega-3", "name": "오메가3"},
        ]
    }


def test_categories_database_failure_uses_common_503_contract() -> None:
    with contract_client(UnavailableProductCategoryService()) as client:
        response = client.get("/api/v1/curation/categories")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_openapi_documents_categories_as_public_unpaginated_get() -> None:
    schema = create_app(Settings(app_env="test")).openapi()
    operation = schema["paths"]["/api/v1/curation/categories"]["get"]

    assert operation["operationId"] == "curation_list_product_categories"
    assert operation.get("security", []) == []
    assert operation.get("parameters", []) == []
    assert set(operation["responses"]) >= {"200", "503"}
