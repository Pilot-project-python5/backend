from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from allyakkkuk.auth.current_user_dependencies import require_current_user
from allyakkkuk.auth.current_user_service import AuthenticatedUser
from allyakkkuk.auth.models import Gender, UserStatus
from allyakkkuk.care.care_item_router import get_care_item_management_service
from allyakkkuk.care.care_item_service import (
    CareItemListItem,
    CareItemListResult,
    CareItemManagementService,
)
from allyakkkuk.core.config import Settings
from allyakkkuk.core.errors import AppError
from allyakkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-3.4")]

NOW = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000215")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000215")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000215")


def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=USER_ID,
        login_id="CareManage215",
        name="복용 관리 계약 사용자",
        email="care-manage-215@example.com",
        status=UserStatus.ACTIVE,
        email_verified_at=NOW,
        birth_date=date(1995, 5, 20),
        gender=Gender.FEMALE,
        height_cm=Decimal("165"),
        weight_kg=Decimal("55"),
        access_token_expires_at=NOW,
        refresh_token_expires_at=NOW,
    )


class StubManagementService:
    def __init__(self, error: AppError | None = None) -> None:
        self.error = error
        self.list_calls: list[tuple[UUID, int, int]] = []
        self.delete_calls: list[tuple[UUID, UUID]] = []

    def list_items(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
    ) -> CareItemListResult:
        self.list_calls.append((user_id, page, page_size))
        if self.error is not None:
            raise self.error
        return CareItemListResult(
            items=(
                CareItemListItem(
                    id=ITEM_ID,
                    product_id=PRODUCT_ID,
                    product_type="SUPPLEMENT",
                    brand="복용 관리 브랜드",
                    name="복용 관리 제품",
                    image_url="/static/products/care-manage-215.svg",
                    purchase_date=date(2026, 8, 10),
                    intake_start_date=date(2026, 8, 13),
                    total_quantity=Decimal("60"),
                    quantity_unit="CAPSULE",
                    dose_per_intake=Decimal("1"),
                    intakes_per_day=2,
                    created_at=NOW,
                ),
            ),
            page=page,
            page_size=page_size,
            total=1,
            has_next=False,
        )

    def delete_item(self, *, user_id: UUID, care_item_id: UUID) -> None:
        self.delete_calls.append((user_id, care_item_id))
        if self.error is not None:
            raise self.error


def contract_client(
    service: StubManagementService,
    *,
    authenticated: bool = True,
) -> TestClient:
    application = create_app(Settings(app_env="test"))
    application.dependency_overrides[get_care_item_management_service] = lambda: cast(
        CareItemManagementService, service
    )
    if authenticated:
        application.dependency_overrides[require_current_user] = current_user
    return TestClient(application)


def test_list_contract_returns_private_page_without_internal_fields() -> None:
    service = StubManagementService()

    with contract_client(service) as client:
        response = client.get("/api/v1/care/items")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "items": [
            {
                "id": str(ITEM_ID),
                "product_id": str(PRODUCT_ID),
                "product_type": "SUPPLEMENT",
                "brand": "복용 관리 브랜드",
                "name": "복용 관리 제품",
                "image_url": "/static/products/care-manage-215.svg",
                "purchase_date": "2026-08-10",
                "intake_start_date": "2026-08-13",
                "total_quantity": "60",
                "quantity_unit": "CAPSULE",
                "dose_per_intake": "1",
                "intakes_per_day": 2,
                "created_at": "2026-08-13T09:00:00Z",
            }
        ],
        "page": 1,
        "page_size": 20,
        "total": 1,
        "has_next": False,
    }
    assert service.list_calls == [(USER_ID, 1, 20)]
    assert "user_id" not in response.text
    assert "deleted_at" not in response.text
    assert "nutrient" not in response.text


@pytest.mark.parametrize(
    "params",
    [{"page": 0}, {"page_size": 0}, {"page_size": 101}],
)
def test_list_rejects_invalid_page_contract(params: dict[str, int]) -> None:
    with contract_client(StubManagementService()) as client:
        response = client.get("/api/v1/care/items", params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_list_and_delete_require_authentication() -> None:
    with contract_client(StubManagementService(), authenticated=False) as client:
        listed = client.get("/api/v1/care/items")
        deleted = client.delete(f"/api/v1/care/items/{ITEM_ID}")

    assert listed.status_code == deleted.status_code == 401
    assert listed.json()["error"]["code"] == "AUTH_REQUIRED"
    assert deleted.json()["error"]["code"] == "AUTH_REQUIRED"


def test_delete_contract_returns_no_content_and_no_store() -> None:
    service = StubManagementService()

    with contract_client(service) as client:
        response = client.delete(f"/api/v1/care/items/{ITEM_ID}")

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    assert service.delete_calls == [(USER_ID, ITEM_ID)]


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (
            AppError(
                status_code=404,
                code="CARE_ITEM_NOT_FOUND",
                message="복용 항목을 찾을 수 없습니다.",
            ),
            404,
            "CARE_ITEM_NOT_FOUND",
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
def test_delete_uses_common_error_contract(
    error: AppError,
    status_code: int,
    code: str,
) -> None:
    with contract_client(StubManagementService(error)) as client:
        response = client.delete(f"/api/v1/care/items/{ITEM_ID}")

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code


def test_openapi_documents_protected_list_and_soft_delete() -> None:
    schema = create_app(Settings(app_env="test")).openapi()
    path = schema["paths"]["/api/v1/care/items"]
    delete_path = schema["paths"]["/api/v1/care/items/{care_item_id}"]

    assert path["get"]["operationId"] == "care_list_items"
    assert path["get"]["security"] == [{"AccessCookieAuth": []}]
    assert set(path["get"]["responses"]) >= {"200", "401", "422", "503"}
    parameters = {item["name"]: item for item in path["get"]["parameters"]}
    assert parameters["page"]["schema"]["default"] == 1
    assert parameters["page_size"]["schema"]["default"] == 20
    assert parameters["page_size"]["schema"]["maximum"] == 100

    assert delete_path["delete"]["operationId"] == "care_delete_item"
    assert delete_path["delete"]["security"] == [{"AccessCookieAuth": []}]
    assert set(delete_path["delete"]["responses"]) >= {
        "204",
        "401",
        "404",
        "422",
        "503",
    }

    item_schema = schema["components"]["schemas"]["CareItemListItemResponse"]
    assert "user_id" not in item_schema["properties"]
    assert "deleted_at" not in item_schema["properties"]
    assert "nutrients" not in item_schema["properties"]
