from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from yeongyangkkuk.auth.login_router import (
    LoginCookiePolicy,
    get_login_cookie_policy,
    get_login_service,
)
from yeongyangkkuk.auth.login_service import LoginCommand, LoginResult, LoginService
from yeongyangkkuk.auth.models import UserStatus
from yeongyangkkuk.core.config import Settings
from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-1.2")]

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)
USER_ID = UUID("11111111-1111-4111-8111-111111111111")


class StubLoginService:
    def login(self, command: LoginCommand) -> LoginResult:
        assert command.login_id == "User123"
        assert command.password == "Safe!Pass123"
        return LoginResult(
            user_id=USER_ID,
            login_id="User123",
            name="홍길동",
            status=UserStatus.ACTIVE,
            authenticated_at=NOW,
            access_token="access-token-value",
            refresh_token="refresh-token-value",
            access_token_expires_at=datetime(2026, 8, 11, 9, 15, tzinfo=UTC),
            refresh_token_expires_at=datetime(2026, 8, 25, 9, 0, tzinfo=UTC),
        )


class UnavailableLoginService:
    def login(self, command: LoginCommand) -> LoginResult:
        raise AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="서비스가 아직 준비되지 않았습니다.",
        )


def contract_client(*, secure: bool = False) -> TestClient:
    application = create_app(Settings(app_env="test"))
    stub = cast(LoginService, StubLoginService())
    application.dependency_overrides[get_login_service] = lambda: stub
    application.dependency_overrides[get_login_cookie_policy] = lambda: (
        LoginCookiePolicy(secure=secure)
    )
    return TestClient(application)


def valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "login_id": "User123",
        "password": "Safe!Pass123",
    }
    payload.update(overrides)
    return payload


def test_login_returns_account_summary_and_http_only_cookies() -> None:
    with contract_client() as client:
        response = client.post("/api/v1/auth/login", json=valid_payload())

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(USER_ID),
        "login_id": "User123",
        "name": "홍길동",
        "status": "ACTIVE",
        "authenticated_at": "2026-08-11T09:00:00Z",
        "access_token_expires_at": "2026-08-11T09:15:00Z",
        "refresh_token_expires_at": "2026-08-25T09:00:00Z",
    }
    assert "access-token-value" not in response.text
    assert "refresh-token-value" not in response.text
    cookies = response.headers.get_list("set-cookie")
    assert any(
        item.startswith("yeongyangkkuk_access_token=access-token-value")
        and "HttpOnly" in item
        and "SameSite=lax" in item
        and "Path=/api/v1" in item
        and "Max-Age=900" in item
        and "Secure" not in item
        for item in cookies
    )
    assert any(
        item.startswith("yeongyangkkuk_refresh_token=refresh-token-value")
        and "HttpOnly" in item
        and "SameSite=lax" in item
        and "Path=/api/v1/auth" in item
        and "Max-Age=1209600" in item
        and "Secure" not in item
        for item in cookies
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"


def test_login_cookie_secure_attribute_is_environment_controlled() -> None:
    with contract_client(secure=True) as client:
        response = client.post("/api/v1/auth/login", json=valid_payload())

    assert response.status_code == 200
    assert all("Secure" in item for item in response.headers.get_list("set-cookie"))


def test_login_failure_never_sets_partial_session_cookie() -> None:
    application = create_app(Settings(app_env="test"))
    unavailable = cast(LoginService, UnavailableLoginService())
    application.dependency_overrides[get_login_service] = lambda: unavailable

    with TestClient(application) as client:
        response = client.post("/api/v1/auth/login", json=valid_payload())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert response.headers.get_list("set-cookie") == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("login_id", "bad"),
        ("login_id", "한글아이디"),
        ("password", "short"),
        ("password", "x" * 21),
    ],
)
def test_login_rejects_invalid_request_shape(field: str, value: str) -> None:
    payload = valid_payload()
    payload[field] = value

    with contract_client() as client:
        response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"
    assert response.headers.get_list("set-cookie") == []


def test_openapi_documents_login_cookies_and_errors() -> None:
    application = create_app(Settings(app_env="test"))
    operation = application.openapi()["paths"]["/api/v1/auth/login"]["post"]

    assert operation["operationId"] == "auth_login"
    assert set(operation["responses"]) >= {"200", "401", "403", "422", "503"}
    success_headers = operation["responses"]["200"]["headers"]
    assert "Set-Cookie" in success_headers
    assert "Cache-Control" in success_headers
