from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from yeongyangkkuk.auth.cookies import REFRESH_COOKIE_NAME
from yeongyangkkuk.auth.login_repository import SQLAlchemyLoginRepository
from yeongyangkkuk.auth.login_router import get_login_service
from yeongyangkkuk.auth.login_service import LoginService
from yeongyangkkuk.auth.models import RefreshSession, User, UserStatus
from yeongyangkkuk.auth.passwords import Argon2PasswordHasher
from yeongyangkkuk.auth.session_repository import SQLAlchemySessionRepository
from yeongyangkkuk.auth.session_router import get_session_service
from yeongyangkkuk.auth.session_service import SessionService
from yeongyangkkuk.auth.tokens import JwtSessionTokenIssuer, parse_refresh_token
from yeongyangkkuk.db.session import SessionFactory, get_db_session
from yeongyangkkuk.main import app
from yeongyangkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-1.3")]

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)
PASSWORD = "Safe!Pass123"
PASSWORD_HASHER = Argon2PasswordHasher()
DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash("Dummy!Pass123")
TOKEN_SECRET = "acceptance-test-session-token-secret-at-least-32-characters"


@pytest.fixture
def created_user_ids() -> Iterator[list[UUID]]:
    user_ids: list[UUID] = []
    yield user_ids
    app.dependency_overrides.pop(get_login_service, None)
    app.dependency_overrides.pop(get_session_service, None)
    if user_ids:
        with SessionFactory.begin() as session:
            session.execute(delete(User).where(User.id.in_(user_ids)))


@pytest.fixture
def session_clock() -> Iterator[FakeClock]:
    clock = FakeClock(NOW)
    token_issuer = JwtSessionTokenIssuer(TOKEN_SECRET)

    def override_login_service(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> LoginService:
        return LoginService(
            repository=SQLAlchemyLoginRepository(session),
            password_hasher=PASSWORD_HASHER,
            dummy_password_hash=DUMMY_PASSWORD_HASH,
            token_issuer=token_issuer,
            clock=clock,
        )

    def override_session_service(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> SessionService:
        return SessionService(
            repository=SQLAlchemySessionRepository(session),
            token_rotator=token_issuer,
            clock=clock,
        )

    app.dependency_overrides[get_login_service] = override_login_service
    app.dependency_overrides[get_session_service] = override_session_service
    yield clock


def create_user(created_user_ids: list[UUID]) -> User:
    suffix = uuid4().hex[:8]
    user_id = uuid4()
    created_user_ids.append(user_id)
    user = User(
        id=user_id,
        name="세션 사용자",
        login_id=f"Session{suffix}",
        normalized_login_id=f"session{suffix}",
        email=f"session-{suffix}@example.com",
        normalized_email=f"session-{suffix}@example.com",
        password_hash=PASSWORD_HASHER.hash(PASSWORD),
        email_verified_at=NOW,
        status=UserStatus.ACTIVE.value,
        created_at=NOW,
        updated_at=NOW,
    )
    with SessionFactory.begin() as session:
        session.add(user)
    return user


def login(client: TestClient, user: User) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"login_id": user.login_id, "password": PASSWORD},
    )
    assert response.status_code == 200
    refresh_token = response.cookies.get(REFRESH_COOKIE_NAME)
    assert isinstance(refresh_token, str)
    return refresh_token


def refresh_headers(token: str) -> dict[str, str]:
    return {"Cookie": f"{REFRESH_COOKIE_NAME}={token}"}


def test_refresh_rotates_same_session_with_absolute_expiration(
    created_user_ids: list[UUID],
    session_clock: FakeClock,
) -> None:
    user = create_user(created_user_ids)
    with TestClient(app) as client:
        old_token = login(client, user)
        parts = parse_refresh_token(old_token)
        assert parts is not None
        session_clock.advance(timedelta(hours=1))
        response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    new_token = response.cookies.get(REFRESH_COOKIE_NAME)
    assert new_token is not None and new_token != old_token
    new_parts = parse_refresh_token(new_token)
    assert new_parts is not None
    assert new_parts.session_id == parts.session_id
    assert response.json()["access_token_expires_at"] == "2026-08-11T10:15:00Z"
    assert response.json()["refresh_token_expires_at"] == "2026-08-25T09:00:00Z"
    with SessionFactory() as session:
        stored = session.get(RefreshSession, parts.session_id)
    assert stored is not None
    assert stored.last_used_at == session_clock.now()
    assert stored.expires_at == NOW + timedelta(days=14)
    assert stored.revoked_at is None


def test_reusing_rotated_token_revokes_new_session(
    created_user_ids: list[UUID],
    session_clock: FakeClock,
) -> None:
    user = create_user(created_user_ids)
    with TestClient(app) as client:
        old_token = login(client, user)
        session_clock.advance(timedelta(minutes=1))
        rotated = client.post("/api/v1/auth/refresh")
        new_token = rotated.cookies.get(REFRESH_COOKIE_NAME)
        assert new_token is not None
        replay = client.post(
            "/api/v1/auth/refresh",
            headers=refresh_headers(old_token),
        )
        latest = client.post(
            "/api/v1/auth/refresh",
            headers=refresh_headers(new_token),
        )

    assert replay.status_code == latest.status_code == 401
    assert replay.json()["error"]["code"] == "AUTH_SESSION_INVALID"
    parts = parse_refresh_token(old_token)
    assert parts is not None
    with SessionFactory() as session:
        stored = session.get(RefreshSession, parts.session_id)
    assert stored is not None
    assert stored.revoked_at == session_clock.now()


def test_refresh_at_absolute_expiration_is_invalid(
    created_user_ids: list[UUID],
    session_clock: FakeClock,
) -> None:
    user = create_user(created_user_ids)
    with TestClient(app) as client:
        login(client, user)
        session_clock.advance(timedelta(days=14))
        response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_SESSION_INVALID"


def test_ineligible_account_refresh_revokes_session(
    created_user_ids: list[UUID],
    session_clock: FakeClock,
) -> None:
    user = create_user(created_user_ids)
    with TestClient(app) as client:
        refresh_token = login(client, user)
        with SessionFactory.begin() as session:
            session.execute(
                update(User)
                .where(User.id == user.id)
                .values(status=UserStatus.SUSPENDED.value)
            )
        response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    parts = parse_refresh_token(refresh_token)
    assert parts is not None
    with SessionFactory() as session:
        stored = session.get(RefreshSession, parts.session_id)
    assert stored is not None
    assert stored.revoked_at == session_clock.now()


def test_logout_revokes_only_current_device_session(
    created_user_ids: list[UUID],
    session_clock: FakeClock,
) -> None:
    user = create_user(created_user_ids)
    with TestClient(app) as first_client, TestClient(app) as second_client:
        first_token = login(first_client, user)
        second_token = login(second_client, user)
        logout_response = first_client.post("/api/v1/auth/logout")
        second_refresh = second_client.post("/api/v1/auth/refresh")

    assert logout_response.status_code == 204
    assert logout_response.cookies.get(REFRESH_COOKIE_NAME) is None
    assert second_refresh.status_code == 200
    first_parts = parse_refresh_token(first_token)
    second_parts = parse_refresh_token(second_token)
    assert first_parts is not None and second_parts is not None
    with SessionFactory() as session:
        first = session.get(RefreshSession, first_parts.session_id)
        second = session.get(RefreshSession, second_parts.session_id)
    assert first is not None and first.revoked_at == session_clock.now()
    assert second is not None and second.revoked_at is None
