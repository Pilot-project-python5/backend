from __future__ import annotations

from typing import cast

import pytest
from fastapi.testclient import TestClient

from yeongyangkkuk.auth.router import get_signup_validation_service
from yeongyangkkuk.auth.service import (
    SignupValidationCommand,
    SignupValidationResult,
    SignupValidationService,
)
from yeongyangkkuk.core.config import Settings
from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-1.1.2")]


class StubSignupValidationService:
    def __init__(self) -> None:
        self.calls = 0

    def validate(self, command: SignupValidationCommand) -> SignupValidationResult:
        self.calls += 1
        return SignupValidationResult(valid=True, issues=())


class FailingSignupValidationService:
    def validate(self, command: SignupValidationCommand) -> SignupValidationResult:
        raise AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="서비스가 아직 준비되지 않았습니다.",
        )


def valid_payload() -> dict[str, object]:
    return {
        "name": "홍길동",
        "login_id": "User123",
        "password": "Safe!Pass123",
        "password_confirmation": "Safe!Pass123",
        "email": "User@example.com",
        "birth_date": "1995-05-20",
        "gender": "MALE",
        "height_cm": 175,
        "weight_kg": 70,
    }


def contract_client(service: SignupValidationService) -> TestClient:
    application = create_app(Settings(app_env="test"))
    application.dependency_overrides[get_signup_validation_service] = lambda: service
    return TestClient(application)


def test_signup_validation_success_contract_excludes_sensitive_fields() -> None:
    stub = StubSignupValidationService()

    with contract_client(cast(SignupValidationService, stub)) as client:
        response = client.post(
            "/api/v1/auth/signup/validation",
            json=valid_payload(),
        )

    assert response.status_code == 200
    assert response.json() == {"valid": True, "issues": []}
    assert "password" not in response.text
    assert "email" not in response.text
    assert stub.calls == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "   "),
        ("login_id", "한글아이디"),
        ("password", "onlyletters"),
        ("email", "not-an-email"),
        ("gender", "UNKNOWN"),
        ("height_cm", 49),
        ("weight_kg", 501),
    ],
)
def test_signup_validation_rejects_invalid_fields(
    field: str,
    value: object,
) -> None:
    payload = valid_payload()
    payload[field] = value
    if field == "password":
        payload["password_confirmation"] = value
    stub = StubSignupValidationService()

    with contract_client(cast(SignupValidationService, stub)) as client:
        response = client.post(
            "/api/v1/auth/signup/validation",
            json=payload,
        )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_FAILED"
    assert any(field in item["field"] for item in body["error"]["fields"])
    assert stub.calls == 0


def test_signup_validation_rejects_password_confirmation_mismatch() -> None:
    payload = valid_payload()
    payload["password_confirmation"] = "Different!123"
    stub = StubSignupValidationService()

    with contract_client(cast(SignupValidationService, stub)) as client:
        response = client.post(
            "/api/v1/auth/signup/validation",
            json=payload,
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"
    assert stub.calls == 0


def test_signup_validation_database_failure_contract() -> None:
    stub = cast(SignupValidationService, FailingSignupValidationService())

    with contract_client(stub) as client:
        response = client.post(
            "/api/v1/auth/signup/validation",
            json=valid_payload(),
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "PostgreSQL" not in response.text


def test_openapi_documents_signup_validation_contract() -> None:
    application = create_app(Settings(app_env="test"))

    operation = application.openapi()["paths"]["/api/v1/auth/signup/validation"]["post"]

    assert operation["operationId"] == "auth_validate_signup"
    assert set(operation["responses"]) >= {"200", "422", "503"}
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    assert request_schema["$ref"].endswith("/SignupRequest")
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert response_schema["$ref"].endswith("/SignupValidationResponse")
