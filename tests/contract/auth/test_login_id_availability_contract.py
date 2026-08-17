from __future__ import annotations

from typing import cast

import pytest
from fastapi.testclient import TestClient

from yeongyangkkuk.auth.router import get_login_id_availability_service
from yeongyangkkuk.auth.service import (
    LoginIdAvailabilityResult,
    LoginIdAvailabilityService,
)
from yeongyangkkuk.core.config import Settings
from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-1.1.1")]


class StubLoginIdAvailabilityService:
    def check(self, login_id: str) -> LoginIdAvailabilityResult:
        return LoginIdAvailabilityResult(login_id=login_id, available=True)


class FailingLoginIdAvailabilityService:
    def check(self, login_id: str) -> LoginIdAvailabilityResult:
        raise AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="서비스가 아직 준비되지 않았습니다.",
        )


def contract_client() -> TestClient:
    application = create_app(Settings(app_env="test"))
    stub = cast(LoginIdAvailabilityService, StubLoginIdAvailabilityService())
    application.dependency_overrides[get_login_id_availability_service] = lambda: stub
    return TestClient(application)


def test_login_id_availability_success_contract() -> None:
    with contract_client() as client:
        response = client.get(
            "/api/v1/auth/login-id/availability",
            params={"login_id": "User123"},
        )

    assert response.status_code == 200
    assert response.json() == {"login_id": "User123", "available": True}


def test_login_id_availability_database_failure_contract() -> None:
    application = create_app(Settings(app_env="test"))
    stub = cast(LoginIdAvailabilityService, FailingLoginIdAvailabilityService())
    application.dependency_overrides[get_login_id_availability_service] = lambda: stub

    with TestClient(application) as client:
        response = client.get(
            "/api/v1/auth/login-id/availability",
            params={"login_id": "User123"},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "PostgreSQL" not in response.text


@pytest.mark.parametrize(
    "login_id",
    [
        "Ab12",
        "A" * 21,
        "한글아이디",
        "User_123",
        " User123",
    ],
)
def test_login_id_availability_rejects_invalid_login_id(login_id: str) -> None:
    with contract_client() as client:
        response = client.get(
            "/api/v1/auth/login-id/availability",
            params={"login_id": login_id},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_FAILED"
    assert body["error"]["fields"][0]["field"] == "query.login_id"


def test_openapi_documents_login_id_availability_contract() -> None:
    application = create_app(Settings(app_env="test"))

    operation = application.openapi()["paths"]["/api/v1/auth/login-id/availability"][
        "get"
    ]

    assert operation["operationId"] == "auth_check_login_id_availability"
    assert set(operation["responses"]) >= {"200", "422", "503"}
    parameter = next(
        item for item in operation["parameters"] if item["name"] == "login_id"
    )
    assert parameter["in"] == "query"
    assert parameter["schema"]["minLength"] == 5
    assert parameter["schema"]["maxLength"] == 20
