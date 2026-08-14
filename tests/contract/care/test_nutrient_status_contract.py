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
from allyakkkuk.care.care_item_router import get_nutrient_status_service
from allyakkkuk.care.nutrient_status_service import (
    NutrientStatusItem,
    NutrientStatusResult,
    NutrientStatusService,
)
from allyakkkuk.core.config import Settings
from allyakkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-3.6")]

NOW = datetime(2026, 8, 14, 9, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000361")
NUTRIENT_ID = UUID("23000000-0000-4000-8000-000000000001")


def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        USER_ID,
        "Status361",
        "현황 사용자",
        "status@example.com",
        UserStatus.ACTIVE,
        NOW,
        date(1990, 1, 1),
        Gender.FEMALE,
        Decimal("165"),
        Decimal("55"),
        NOW,
        NOW,
    )


class StubService:
    def get_status(self, *, user_id: UUID) -> NutrientStatusResult:
        assert user_id == USER_ID
        return NutrientStatusResult(
            as_of_date=date(2026, 8, 14),
            age=36,
            gender="FEMALE",
            reference_version="KDRI-2025-20260316",
            reference_source_name="2025 한국인 영양소 섭취기준",
            reference_source_url="https://example.com/kdri",
            nutrients=(
                NutrientStatusItem(
                    NUTRIENT_ID,
                    "VITAMIN_C",
                    "비타민 C",
                    Decimal("150"),
                    "MG",
                    True,
                    Decimal("100"),
                    "RNI",
                    Decimal("150.0"),
                ),
            ),
        )


def test_nutrient_status_contract_and_openapi() -> None:
    app = create_app(Settings(app_env="test"))
    app.dependency_overrides[require_current_user] = current_user
    app.dependency_overrides[get_nutrient_status_service] = lambda: cast(
        NutrientStatusService, StubService()
    )
    with TestClient(app) as client:
        response = client.get("/api/v1/care/nutrient-status")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["nutrients"][0] == {
        "nutrient_id": str(NUTRIENT_ID),
        "nutrient_code": "VITAMIN_C",
        "nutrient_name": "비타민 C",
        "daily_amount": "150",
        "unit": "MG",
        "reference_available": True,
        "reference_amount": "100",
        "reference_type": "RNI",
        "achievement_rate_percent": "150",
    }
    operation = app.openapi()["paths"]["/api/v1/care/nutrient-status"]["get"]
    assert operation["operationId"] == "care_get_nutrient_status"
    assert operation["security"] == [{"AccessCookieAuth": []}]
    assert set(operation["responses"]) >= {"200", "401", "503"}


def test_nutrient_status_requires_authentication() -> None:
    app = create_app(Settings(app_env="test"))
    with TestClient(app) as client:
        response = client.get("/api/v1/care/nutrient-status")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
