from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import UUID, uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from allyakkkuk.auth.cookies import ACCESS_COOKIE_NAME
from allyakkkuk.auth.current_user_dependencies import get_current_user_service
from allyakkkuk.auth.current_user_repository import SQLAlchemyCurrentUserRepository
from allyakkkuk.auth.current_user_service import CurrentUserService
from allyakkkuk.auth.login_repository import SQLAlchemyLoginRepository
from allyakkkuk.auth.login_router import get_login_service
from allyakkkuk.auth.login_service import LoginService
from allyakkkuk.auth.models import Gender, HealthProfile, User, UserStatus
from allyakkkuk.auth.passwords import Argon2PasswordHasher
from allyakkkuk.auth.session_repository import SQLAlchemySessionRepository
from allyakkkuk.auth.session_router import get_session_service
from allyakkkuk.auth.session_service import SessionService
from allyakkkuk.auth.tokens import JwtSessionTokenIssuer
from allyakkkuk.db.session import SessionFactory, get_db_session
from allyakkkuk.main import app
from allyakkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-1.4")]

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)
PASSWORD = "Safe!Pass123"
PASSWORD_HASHER = Argon2PasswordHasher()
DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash("Dummy!Pass123")
TOKEN_SECRET = "acceptance-test-current-user-token-secret-at-least-32-characters"


@pytest.fixture
def created_user_ids() -> Iterator[list[UUID]]:
    user_ids: list[UUID] = []
    yield user_ids
    app.dependency_overrides.pop(get_login_service, None)
    app.dependency_overrides.pop(get_session_service, None)
    app.dependency_overrides.pop(get_current_user_service, None)
    if user_ids:
        with SessionFactory.begin() as session:
            session.execute(delete(User).where(User.id.in_(user_ids)))


@pytest.fixture
def auth_clock() -> FakeClock:
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

    def override_current_user_service(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> CurrentUserService:
        return CurrentUserService(
            repository=SQLAlchemyCurrentUserRepository(session),
            token_verifier=token_issuer,
            clock=clock,
        )

    app.dependency_overrides[get_login_service] = override_login_service
    app.dependency_overrides[get_session_service] = override_session_service
    app.dependency_overrides[get_current_user_service] = override_current_user_service
    return clock


def create_user(created_user_ids: list[UUID]) -> User:
    suffix = uuid4().hex[:8]
    user_id = uuid4()
    created_user_ids.append(user_id)
    user = User(
        id=user_id,
        name="현재 사용자",
        login_id=f"Current{suffix}",
        normalized_login_id=f"current{suffix}",
        email=f"current-{suffix}@example.com",
        normalized_email=f"current-{suffix}@example.com",
        password_hash=PASSWORD_HASHER.hash(PASSWORD),
        email_verified_at=NOW,
        status=UserStatus.ACTIVE.value,
        created_at=NOW,
        updated_at=NOW,
    )
    profile = HealthProfile(
        user_id=user_id,
        birth_date=date(1995, 5, 20),
        gender=Gender.MALE.value,
        height_cm=Decimal("175.00"),
        weight_kg=Decimal("70.00"),
        created_at=NOW,
        updated_at=NOW,
    )
    with SessionFactory.begin() as session:
        session.add(user)
        session.flush()
        session.add(profile)
    return user


def login(client: TestClient, user: User) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"login_id": user.login_id, "password": PASSWORD},
    )
    assert response.status_code == 200
    access_token = response.cookies.get(ACCESS_COOKIE_NAME)
    assert isinstance(access_token, str)
    return access_token


def access_header(access_token: str) -> dict[str, str]:
    return {"Cookie": f"{ACCESS_COOKIE_NAME}={access_token}"}


def test_logged_in_user_can_read_current_profile_and_session(
    created_user_ids: list[UUID],
    auth_clock: FakeClock,
) -> None:
    user = create_user(created_user_ids)
    with TestClient(app) as client:
        login(client, user)
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["user"] == {
        "id": str(user.id),
        "login_id": user.login_id,
        "name": "현재 사용자",
        "email": user.email,
        "status": "ACTIVE",
        "email_verified_at": "2026-08-11T09:00:00Z",
        "birth_date": "1995-05-20",
        "gender": "MALE",
        "height_cm": "175.00",
        "weight_kg": "70.00",
    }
    assert body["session"] == {
        "access_token_expires_at": "2026-08-11T09:15:00Z",
        "refresh_token_expires_at": "2026-08-25T09:00:00Z",
    }
    assert auth_clock.now() == NOW


def test_logout_immediately_invalidates_existing_access_token(
    created_user_ids: list[UUID],
    auth_clock: FakeClock,
) -> None:
    user = create_user(created_user_ids)
    with TestClient(app) as client:
        old_access_token = login(client, user)
        logout = client.post("/api/v1/auth/logout")
        response = client.get(
            "/api/v1/auth/me",
            headers=access_header(old_access_token),
        )

    assert logout.status_code == 204
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
    assert auth_clock.now() == NOW


def test_expired_access_requires_explicit_refresh_before_me_succeeds(
    created_user_ids: list[UUID],
    auth_clock: FakeClock,
) -> None:
    user = create_user(created_user_ids)
    with TestClient(app) as client:
        login(client, user)
        auth_clock.advance(timedelta(minutes=15))
        expired = client.get("/api/v1/auth/me")
        refreshed = client.post("/api/v1/auth/refresh")
        current = client.get("/api/v1/auth/me")

    assert expired.status_code == 401
    assert expired.json()["error"]["code"] == "AUTH_REQUIRED"
    assert refreshed.status_code == 200
    assert current.status_code == 200
    assert current.json()["authenticated"] is True
