from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from allyakkkuk.auth.login_repository import SQLAlchemyLoginRepository
from allyakkkuk.auth.login_router import get_login_service
from allyakkkuk.auth.login_service import LoginService
from allyakkkuk.auth.models import RefreshSession, User, UserStatus
from allyakkkuk.auth.passwords import Argon2PasswordHasher
from allyakkkuk.auth.tokens import JwtSessionTokenIssuer
from allyakkkuk.db.session import SessionFactory, get_db_session
from allyakkkuk.main import app
from allyakkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-1.2")]

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)
PASSWORD = "Safe!Pass123"
PASSWORD_HASHER = Argon2PasswordHasher()
DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash("Dummy!Pass123")
TOKEN_SECRET = "acceptance-test-auth-token-secret-at-least-32-characters"


@pytest.fixture
def created_user_ids() -> Iterator[list[UUID]]:
    user_ids: list[UUID] = []
    yield user_ids
    app.dependency_overrides.pop(get_login_service, None)
    if user_ids:
        with SessionFactory.begin() as session:
            session.execute(delete(User).where(User.id.in_(user_ids)))


@pytest.fixture(autouse=True)
def login_service_override() -> Iterator[None]:
    clock = FakeClock(NOW)
    token_issuer = JwtSessionTokenIssuer(TOKEN_SECRET)

    def override_service(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> LoginService:
        return LoginService(
            repository=SQLAlchemyLoginRepository(session),
            password_hasher=PASSWORD_HASHER,
            dummy_password_hash=DUMMY_PASSWORD_HASH,
            token_issuer=token_issuer,
            clock=clock,
        )

    app.dependency_overrides[get_login_service] = override_service
    yield


def create_user(
    created_user_ids: list[UUID],
    *,
    status: UserStatus = UserStatus.ACTIVE,
    verified: bool = True,
) -> User:
    suffix = uuid4().hex[:8]
    user_id = uuid4()
    created_user_ids.append(user_id)
    user = User(
        id=user_id,
        name="로그인 사용자",
        login_id=f"Login{suffix}",
        normalized_login_id=f"login{suffix}",
        email=f"login-{suffix}@example.com",
        normalized_email=f"login-{suffix}@example.com",
        password_hash=PASSWORD_HASHER.hash(PASSWORD),
        email_verified_at=NOW if verified else None,
        status=status.value,
        created_at=NOW,
        updated_at=NOW,
    )
    with SessionFactory.begin() as session:
        session.add(user)
    return user


def login_payload(user: User, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "login_id": user.login_id.swapcase(),
        "password": PASSWORD,
    }
    payload.update(overrides)
    return payload


def test_active_user_login_sets_cookies_and_stores_only_refresh_hash(
    created_user_ids: list[UUID],
) -> None:
    user = create_user(created_user_ids)

    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json=login_payload(user))

    assert response.status_code == 200
    assert response.json()["user_id"] == str(user.id)
    assert response.json()["status"] == "ACTIVE"
    assert response.json()["access_token_expires_at"] == "2026-08-11T09:15:00Z"
    assert response.json()["refresh_token_expires_at"] == "2026-08-25T09:00:00Z"
    access_token = response.cookies.get("allyakkkuk_access_token")
    refresh_token = response.cookies.get("allyakkkuk_refresh_token")
    assert access_token is not None
    assert refresh_token is not None
    assert access_token not in response.text
    assert refresh_token not in response.text

    with SessionFactory() as session:
        stored = session.scalar(
            select(RefreshSession).where(RefreshSession.user_id == user.id)
        )
    assert stored is not None
    assert stored.token_hash != refresh_token
    assert refresh_token not in stored.token_hash
    assert stored.revoked_at is None
    assert stored.last_used_at is None


def test_repeated_login_creates_distinct_device_sessions(
    created_user_ids: list[UUID],
) -> None:
    user = create_user(created_user_ids)

    with TestClient(app) as first_client, TestClient(app) as second_client:
        first = first_client.post("/api/v1/auth/login", json=login_payload(user))
        second = second_client.post("/api/v1/auth/login", json=login_payload(user))

    assert first.status_code == second.status_code == 200
    assert first.cookies.get("allyakkkuk_refresh_token") != second.cookies.get(
        "allyakkkuk_refresh_token"
    )
    with SessionFactory() as session:
        session_count = session.scalar(
            select(func.count())
            .select_from(RefreshSession)
            .where(RefreshSession.user_id == user.id)
        )
    assert session_count == 2


@pytest.mark.parametrize(
    ("status", "verified", "error_code"),
    [
        (UserStatus.PENDING_EMAIL_VERIFICATION, False, "AUTH_EMAIL_UNVERIFIED"),
        (UserStatus.SUSPENDED, True, "AUTH_ACCOUNT_SUSPENDED"),
    ],
)
def test_login_rejects_ineligible_account_without_session(
    created_user_ids: list[UUID],
    status: UserStatus,
    verified: bool,
    error_code: str,
) -> None:
    user = create_user(created_user_ids, status=status, verified=verified)

    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json=login_payload(user))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == error_code
    assert response.headers.get_list("set-cookie") == []
    with SessionFactory() as session:
        count = session.scalar(
            select(func.count())
            .select_from(RefreshSession)
            .where(RefreshSession.user_id == user.id)
        )
    assert count == 0


def test_unknown_id_and_wrong_password_return_same_error_without_session(
    created_user_ids: list[UUID],
) -> None:
    user = create_user(created_user_ids)

    with TestClient(app) as client:
        unknown = client.post(
            "/api/v1/auth/login",
            json={"login_id": "Nobody1", "password": PASSWORD},
        )
        wrong = client.post(
            "/api/v1/auth/login",
            json=login_payload(user, password="Wrong!Pass123"),
        )

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["error"] == {
        **wrong.json()["error"],
        "request_id": unknown.json()["error"]["request_id"],
    }
    assert unknown.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
    assert unknown.headers.get_list("set-cookie") == []
    assert wrong.headers.get_list("set-cookie") == []
    with SessionFactory() as session:
        count = session.scalar(
            select(func.count())
            .select_from(RefreshSession)
            .where(RefreshSession.user_id == user.id)
        )
    assert count == 0
