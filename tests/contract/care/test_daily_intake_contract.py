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
from allyakkkuk.care.care_item_router import get_daily_intake_service
from allyakkkuk.care.daily_intake_service import DailyIntakeItem, DailyIntakeService
from allyakkkuk.core.config import Settings
from allyakkkuk.core.errors import AppError
from allyakkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-3.5")]

NOW = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000351")
NUTRIENT_ID = UUID("23000000-0000-4000-8000-000000000352")


def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=USER_ID,
        login_id="DailyIntake351",
        name="일일 섭취량 계약 사용자",
        email="daily-intake-351@example.com",
        status=UserStatus.ACTIVE,
        email_verified_at=NOW,
        birth_date=date(1995, 5, 20),
        gender=Gender.FEMALE,
        height_cm=Decimal("165"),
        weight_kg=Decimal("55"),
        access_token_expires_at=NOW,
        refresh_token_expires_at=NOW,
    )


class StubDailyIntakeService:
    def __init__(
        self,
        error: AppError | None = None,
        *,
        items: tuple[DailyIntakeItem, ...] | None = None,
    ) -> None:
        self.error = error
        self.calls: list[UUID] = []
        self.items = items

    def get_daily_intake(self, *, user_id: UUID) -> tuple[DailyIntakeItem, ...]:
        self.calls.append(user_id)
        if self.error is not None:
            raise self.error
        if self.items is not None:
            return self.items
        return (
            DailyIntakeItem(
                nutrient_id=NUTRIENT_ID,
                nutrient_code="VITAMIN_C",
                nutrient_name="비타민 C",
                daily_amount=Decimal("3250.0000"),
                unit="MG",
            ),
        )


def contract_client(
    service: StubDailyIntakeService,
    *,
    authenticated: bool = True,
) -> TestClient:
    application = create_app(Settings(app_env="test"))
    application.dependency_overrides[get_daily_intake_service] = lambda: cast(
        DailyIntakeService, service
    )
    if authenticated:
        application.dependency_overrides[require_current_user] = current_user
    return TestClient(application)


def test_daily_intake_contract_returns_normalized_private_response() -> None:
    service = StubDailyIntakeService()

    with contract_client(service) as client:
        response = client.get("/api/v1/care/daily-intake")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "nutrients": [
            {
                "nutrient_id": str(NUTRIENT_ID),
                "nutrient_code": "VITAMIN_C",
                "nutrient_name": "비타민 C",
                "daily_amount": "3250",
                "unit": "MG",
            }
        ]
    }
    assert service.calls == [USER_ID]
    assert "user_id" not in response.text
    assert "care_item_id" not in response.text


def test_daily_intake_contract_returns_empty_array() -> None:
    service = StubDailyIntakeService(items=())

    with contract_client(service) as client:
        response = client.get("/api/v1/care/daily-intake")

    assert response.status_code == 200
    assert response.json() == {"nutrients": []}


def test_daily_intake_requires_authentication() -> None:
    with contract_client(StubDailyIntakeService(), authenticated=False) as client:
        response = client.get("/api/v1/care/daily-intake")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_daily_intake_uses_common_service_unavailable_error() -> None:
    error = AppError(
        status_code=503,
        code="SERVICE_UNAVAILABLE",
        message="서비스가 아직 준비되지 않았습니다.",
    )

    with contract_client(StubDailyIntakeService(error)) as client:
        response = client.get("/api/v1/care/daily-intake")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_openapi_documents_daily_intake_contract() -> None:
    schema = create_app(Settings(app_env="test")).openapi()
    operation = schema["paths"]["/api/v1/care/daily-intake"]["get"]

    assert operation["operationId"] == "care_get_daily_intake"
    assert operation["security"] == [{"AccessCookieAuth": []}]
    assert set(operation["responses"]) >= {"200", "401", "503"}
    assert "parameters" not in operation
    response_schema = schema["components"]["schemas"]["DailyIntakeResponse"]
    assert response_schema["required"] == ["nutrients"]
