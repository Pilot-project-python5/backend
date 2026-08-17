from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from yeongyangkkuk.auth.current_user_dependencies import require_current_user
from yeongyangkkuk.auth.current_user_service import AuthenticatedUser
from yeongyangkkuk.auth.models import Gender, UserStatus
from yeongyangkkuk.core.config import Settings
from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-1.4")]

USER_ID = UUID("11111111-1111-4111-8111-111111111111")
NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)


def authenticated_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=USER_ID,
        login_id="User123",
        name="홍길동",
        email="user@example.com",
        status=UserStatus.ACTIVE,
        email_verified_at=NOW,
        birth_date=date(1995, 5, 20),
        gender=Gender.MALE,
        height_cm=Decimal("175.00"),
        weight_kg=Decimal("70.00"),
        access_token_expires_at=datetime(2026, 8, 11, 9, 15, tzinfo=UTC),
        refresh_token_expires_at=datetime(2026, 8, 25, 9, 0, tzinfo=UTC),
    )


def contract_client(override: object | None = None) -> TestClient:
    application = create_app(Settings(app_env="test"))
    principal = authenticated_user() if override is None else override
    application.dependency_overrides[require_current_user] = lambda: cast(
        AuthenticatedUser, principal
    )
    return TestClient(application)


def test_me_returns_current_user_and_session_without_tokens() -> None:
    with contract_client() as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": True,
        "user": {
            "id": str(USER_ID),
            "login_id": "User123",
            "name": "홍길동",
            "email": "user@example.com",
            "status": "ACTIVE",
            "email_verified_at": "2026-08-11T09:00:00Z",
            "birth_date": "1995-05-20",
            "gender": "MALE",
            "height_cm": "175.00",
            "weight_kg": "70.00",
        },
        "session": {
            "access_token_expires_at": "2026-08-11T09:15:00Z",
            "refresh_token_expires_at": "2026-08-25T09:00:00Z",
        },
    }
    assert "access_token" not in response.json()
    assert "refresh_token" not in response.json()
    assert "password_hash" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers.get_list("set-cookie") == []


@pytest.mark.parametrize(
    ("status_code", "code", "message"),
    [
        (401, "AUTH_REQUIRED", "인증이 필요합니다."),
        (503, "SERVICE_UNAVAILABLE", "서비스가 아직 준비되지 않았습니다."),
    ],
)
def test_me_preserves_authentication_error_contract_without_cookie_changes(
    status_code: int,
    code: str,
    message: str,
) -> None:
    def fail() -> AuthenticatedUser:
        raise AppError(status_code=status_code, code=code, message=message)

    application = create_app(Settings(app_env="test"))
    application.dependency_overrides[require_current_user] = fail
    with TestClient(application) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code
    assert response.headers.get_list("set-cookie") == []


def test_openapi_documents_cookie_security_and_me_responses() -> None:
    schema = create_app(Settings(app_env="test")).openapi()
    operation = schema["paths"]["/api/v1/auth/me"]["get"]

    assert operation["operationId"] == "auth_get_current_user"
    assert operation["security"] == [{"AccessCookieAuth": []}]
    assert set(operation["responses"]) >= {"200", "401", "503"}
    assert schema["components"]["securitySchemes"]["AccessCookieAuth"] == {
        "type": "apiKey",
        "in": "cookie",
        "name": "yeongyangkkuk_access_token",
        "description": "HttpOnly access JWT 쿠키",
    }
