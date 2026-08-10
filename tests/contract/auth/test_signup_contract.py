from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from allyakkkuk.auth.models import UserStatus
from allyakkkuk.auth.router import get_signup_service
from allyakkkuk.auth.service import SignupCommand, SignupResult, SignupService
from allyakkkuk.core.config import Settings
from allyakkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-1.1")]


class StubSignupService:
    def signup(self, command: SignupCommand) -> SignupResult:
        return SignupResult(
            id=UUID("11111111-1111-4111-8111-111111111111"),
            login_id=command.login_id,
            email=command.email,
            status=UserStatus.PENDING_EMAIL_VERIFICATION,
            created_at=datetime(2026, 8, 10, 9, 0, tzinfo=UTC),
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


def contract_client() -> TestClient:
    application = create_app(Settings(app_env="test"))
    stub = cast(SignupService, StubSignupService())
    application.dependency_overrides[get_signup_service] = lambda: stub
    return TestClient(application)


def test_signup_success_contract_excludes_passwords() -> None:
    with contract_client() as client:
        response = client.post("/api/v1/auth/signup", json=valid_payload())

    assert response.status_code == 201
    assert response.json() == {
        "id": "11111111-1111-4111-8111-111111111111",
        "login_id": "User123",
        "email": "User@example.com",
        "status": "PENDING_EMAIL_VERIFICATION",
        "email_verification_required": True,
        "created_at": "2026-08-10T09:00:00Z",
    }
    assert "password" not in response.text


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("login_id", "한글아이디"),
        ("password", "12345678!"),
        ("password", "onlyletters"),
        ("password", "Password1"),
        ("password", "Safe비번1!"),
        ("password", "Short1!"),
        ("gender", "UNKNOWN"),
        ("height_cm", 49),
        ("weight_kg", 501),
    ],
)
def test_signup_rejects_invalid_fields(field: str, value: object) -> None:
    payload = valid_payload()
    payload[field] = value
    if field == "password":
        payload["password_confirmation"] = value

    with contract_client() as client:
        response = client.post("/api/v1/auth/signup", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_FAILED"
    assert any(field in item["field"] for item in body["error"]["fields"])


def test_signup_rejects_password_confirmation_mismatch() -> None:
    payload = valid_payload()
    payload["password_confirmation"] = "Different!123"

    with contract_client() as client:
        response = client.post("/api/v1/auth/signup", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"
    assert response.json()["error"]["fields"][0]["field"].endswith(
        "password_confirmation"
    )


def test_openapi_documents_signup_contract_and_errors() -> None:
    application = create_app(Settings(app_env="test"))

    operation = application.openapi()["paths"]["/api/v1/auth/signup"]["post"]

    assert operation["operationId"] == "auth_signup"
    assert set(operation["responses"]) >= {"201", "409", "422", "503"}
    assert "examples" in application.openapi()["components"]["schemas"]["SignupRequest"]
