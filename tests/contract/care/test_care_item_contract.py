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
from allyakkkuk.care.care_item_router import get_care_item_service
from allyakkkuk.care.care_item_service import (
    CareItemRegistrationCommand,
    CareItemRegistrationResult,
    CareItemService,
)
from allyakkkuk.core.config import Settings
from allyakkkuk.core.errors import AppError
from allyakkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-3.1")]

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000031")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000031")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000031")


def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=USER_ID,
        login_id="CareUser31",
        name="복용 사용자",
        email="care31@example.com",
        status=UserStatus.ACTIVE,
        email_verified_at=NOW,
        birth_date=date(1995, 5, 20),
        gender=Gender.MALE,
        height_cm=Decimal("175"),
        weight_kg=Decimal("70"),
        access_token_expires_at=NOW,
        refresh_token_expires_at=NOW,
    )


class StubCareItemService:
    def __init__(self, error: AppError | None = None) -> None:
        self.error = error
        self.calls: list[tuple[UUID, CareItemRegistrationCommand]] = []

    def register(
        self,
        *,
        user_id: UUID,
        command: CareItemRegistrationCommand,
    ) -> CareItemRegistrationResult:
        self.calls.append((user_id, command))
        if self.error is not None:
            raise self.error
        return CareItemRegistrationResult(
            id=ITEM_ID,
            product_id=command.product_id,
            purchase_date=command.purchase_date,
            intake_start_date=command.intake_start_date,
            total_quantity=command.total_quantity,
            dose_per_intake=command.dose_per_intake,
            intakes_per_day=command.intakes_per_day,
            created_at=NOW,
        )


def contract_client(
    service: StubCareItemService,
    *,
    authenticated: bool = True,
) -> TestClient:
    application = create_app(Settings(app_env="test"))
    application.dependency_overrides[get_care_item_service] = lambda: cast(
        CareItemService, service
    )
    if authenticated:
        application.dependency_overrides[require_current_user] = current_user
    return TestClient(application)


def valid_payload() -> dict[str, object]:
    return {
        "product_id": str(PRODUCT_ID),
        "purchase_date": "2026-08-10",
        "intake_start_date": "2026-08-12",
        "total_quantity": "60",
        "dose_per_intake": "1.5",
        "intakes_per_day": 2,
    }


def test_register_contract_returns_created_item_without_user_id() -> None:
    service = StubCareItemService()

    with contract_client(service) as client:
        response = client.post("/api/v1/care/items", json=valid_payload())

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "id": str(ITEM_ID),
        "product_id": str(PRODUCT_ID),
        "purchase_date": "2026-08-10",
        "intake_start_date": "2026-08-12",
        "total_quantity": "60",
        "dose_per_intake": "1.5",
        "intakes_per_day": 2,
        "created_at": "2026-08-12T09:00:00Z",
    }
    assert service.calls[0][0] == USER_ID


def test_register_requires_authentication() -> None:
    with contract_client(StubCareItemService(), authenticated=False) as client:
        response = client.post("/api/v1/care/items", json=valid_payload())

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"total_quantity": "0"}, "body.total_quantity"),
        ({"dose_per_intake": "1000000000"}, "body.dose_per_intake"),
        ({"intakes_per_day": 0}, "body.intakes_per_day"),
        ({"intakes_per_day": 25}, "body.intakes_per_day"),
    ],
)
def test_register_rejects_invalid_field_contract(
    overrides: dict[str, object],
    field: str,
) -> None:
    payload = {**valid_payload(), **overrides}

    with contract_client(StubCareItemService()) as client:
        response = client.post("/api/v1/care/items", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"
    assert response.json()["error"]["fields"][0]["field"] == field


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
def test_register_uses_common_error_contract(
    error: AppError,
    status_code: int,
    code: str,
) -> None:
    with contract_client(StubCareItemService(error)) as client:
        response = client.post("/api/v1/care/items", json=valid_payload())

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code


def test_openapi_documents_protected_care_item_registration() -> None:
    schema = create_app(Settings(app_env="test")).openapi()
    operation = schema["paths"]["/api/v1/care/items"]["post"]

    assert operation["operationId"] == "care_register_item"
    assert operation["security"] == [{"AccessCookieAuth": []}]
    assert set(operation["responses"]) >= {"201", "401", "404", "422", "503"}
    assert (
        "user_id"
        not in schema["components"]["schemas"]["CareItemCreateRequest"]["properties"]
    )
