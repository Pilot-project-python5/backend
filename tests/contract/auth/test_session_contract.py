from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest
from fastapi.testclient import TestClient

from allyakkkuk.auth.cookies import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    SessionCookiePolicy,
)
from allyakkkuk.auth.session_router import (
    get_session_cookie_policy,
    get_session_service,
)
from allyakkkuk.auth.session_service import SessionRefreshResult, SessionService
from allyakkkuk.core.config import Settings
from allyakkkuk.core.errors import AppError
from allyakkkuk.main import create_app

pytestmark = [pytest.mark.contract, pytest.mark.feature("F-1.3")]

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)
REFRESH_EXPIRES_AT = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


class StubSessionService:
    def __init__(self) -> None:
        self.refresh_tokens: list[str | None] = []
        self.logout_tokens: list[str | None] = []

    def refresh(self, raw_token: str | None) -> SessionRefreshResult:
        self.refresh_tokens.append(raw_token)
        return SessionRefreshResult(
            authenticated_at=NOW,
            access_token="rotated-access-token",
            refresh_token="rotated-refresh-token",
            access_token_expires_at=datetime(2026, 8, 11, 9, 15, tzinfo=UTC),
            refresh_token_expires_at=REFRESH_EXPIRES_AT,
        )

    def logout(self, raw_token: str | None) -> None:
        self.logout_tokens.append(raw_token)


class InvalidSessionService(StubSessionService):
    def refresh(self, raw_token: str | None) -> SessionRefreshResult:
        raise AppError(
            status_code=401,
            code="AUTH_SESSION_INVALID",
            message="유효하지 않은 인증 세션입니다.",
        )


class UnavailableSessionService(StubSessionService):
    def refresh(self, raw_token: str | None) -> SessionRefreshResult:
        raise self._error()

    def logout(self, raw_token: str | None) -> None:
        raise self._error()

    @staticmethod
    def _error() -> AppError:
        return AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="서비스가 아직 준비되지 않았습니다.",
        )


def contract_client(
    service: StubSessionService,
    *,
    secure: bool = False,
) -> TestClient:
    application = create_app(Settings(app_env="test"))
    typed_service = cast(SessionService, service)
    application.dependency_overrides[get_session_service] = lambda: typed_service
    application.dependency_overrides[get_session_cookie_policy] = lambda: (
        SessionCookiePolicy(secure=secure)
    )
    return TestClient(application)


def cookie_header(value: str = "old-refresh-token") -> dict[str, str]:
    return {"Cookie": f"{REFRESH_COOKIE_NAME}={value}"}


def test_refresh_rotates_http_only_cookies_with_remaining_lifetime() -> None:
    service = StubSessionService()

    with contract_client(service) as client:
        response = client.post("/api/v1/auth/refresh", headers=cookie_header())

    assert response.status_code == 200
    assert service.refresh_tokens == ["old-refresh-token"]
    assert response.json() == {
        "authenticated_at": "2026-08-11T09:00:00Z",
        "access_token_expires_at": "2026-08-11T09:15:00Z",
        "refresh_token_expires_at": "2026-08-12T09:00:00Z",
    }
    assert "rotated-access-token" not in response.text
    assert "rotated-refresh-token" not in response.text
    cookies = response.headers.get_list("set-cookie")
    assert any(
        item.startswith(f"{ACCESS_COOKIE_NAME}=rotated-access-token")
        and "HttpOnly" in item
        and "SameSite=lax" in item
        and "Path=/api/v1" in item
        and "Max-Age=900" in item
        and "Secure" not in item
        for item in cookies
    )
    assert any(
        item.startswith(f"{REFRESH_COOKIE_NAME}=rotated-refresh-token")
        and "HttpOnly" in item
        and "SameSite=lax" in item
        and "Path=/api/v1/auth" in item
        and "Max-Age=86400" in item
        and "Secure" not in item
        for item in cookies
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"


def test_refresh_secure_cookie_policy_is_environment_controlled() -> None:
    with contract_client(StubSessionService(), secure=True) as client:
        response = client.post("/api/v1/auth/refresh", headers=cookie_header())

    assert response.status_code == 200
    assert all("Secure" in item for item in response.headers.get_list("set-cookie"))


def test_invalid_refresh_clears_both_authentication_cookies() -> None:
    with contract_client(InvalidSessionService()) as client:
        response = client.post("/api/v1/auth/refresh", headers=cookie_header())

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_SESSION_INVALID"
    cookies = response.headers.get_list("set-cookie")
    assert any(
        item.startswith(f'{ACCESS_COOKIE_NAME}=""')
        and "Max-Age=0" in item
        and "Path=/api/v1" in item
        for item in cookies
    )
    assert any(
        item.startswith(f'{REFRESH_COOKIE_NAME}=""')
        and "Max-Age=0" in item
        and "Path=/api/v1/auth" in item
        for item in cookies
    )


def test_refresh_database_failure_does_not_change_cookies() -> None:
    with contract_client(UnavailableSessionService()) as client:
        response = client.post("/api/v1/auth/refresh", headers=cookie_header())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert response.headers.get_list("set-cookie") == []


def test_logout_is_204_and_clears_both_cookies() -> None:
    service = StubSessionService()

    with contract_client(service) as client:
        response = client.post("/api/v1/auth/logout", headers=cookie_header())

    assert response.status_code == 204
    assert response.content == b""
    assert service.logout_tokens == ["old-refresh-token"]
    cookies = response.headers.get_list("set-cookie")
    assert len(cookies) == 2
    assert all("Max-Age=0" in item for item in cookies)
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"


def test_logout_database_failure_does_not_clear_cookies() -> None:
    with contract_client(UnavailableSessionService()) as client:
        response = client.post("/api/v1/auth/logout", headers=cookie_header())

    assert response.status_code == 503
    assert response.headers.get_list("set-cookie") == []


def test_openapi_documents_refresh_and_logout_cookie_contracts() -> None:
    application = create_app(Settings(app_env="test"))
    paths = application.openapi()["paths"]
    refresh = paths["/api/v1/auth/refresh"]["post"]
    logout = paths["/api/v1/auth/logout"]["post"]

    assert refresh["operationId"] == "auth_refresh_session"
    assert set(refresh["responses"]) >= {"200", "401", "503"}
    assert "Set-Cookie" in refresh["responses"]["200"]["headers"]
    assert any(item["in"] == "cookie" for item in refresh["parameters"])
    assert logout["operationId"] == "auth_logout"
    assert set(logout["responses"]) >= {"204", "503"}
    assert "Set-Cookie" in logout["responses"]["204"]["headers"]
