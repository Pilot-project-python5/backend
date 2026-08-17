from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from yeongyangkkuk.auth.models import HealthProfile, User
from yeongyangkkuk.db.session import SessionFactory
from yeongyangkkuk.main import app

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-1.1")]


@pytest.fixture(autouse=True)
def clean_signup_tables() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(HealthProfile))
        session.execute(delete(User))
    yield
    with SessionFactory.begin() as session:
        session.execute(delete(HealthProfile))
        session.execute(delete(User))


def valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
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
    payload.update(overrides)
    return payload


def test_signup_creates_an_unverified_user_and_profile() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/signup", json=valid_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING_EMAIL_VERIFICATION"
    assert body["email_verification_required"] is True
    assert "password" not in response.text

    with SessionFactory() as session:
        user = session.scalar(select(User).where(User.normalized_login_id == "user123"))
        assert user is not None
        profile = session.get(HealthProfile, user.id)

    assert user.normalized_email == "user@example.com"
    assert user.email_verified_at is None
    assert user.password_hash.startswith("$argon2id$")
    assert "Safe!Pass123" not in user.password_hash
    assert profile is not None
    assert str(profile.height_cm) == "175.00"


def test_signup_rejects_a_case_insensitive_duplicate_login_id() -> None:
    with TestClient(app) as client:
        first = client.post("/api/v1/auth/signup", json=valid_payload())
        second = client.post(
            "/api/v1/auth/signup",
            json=valid_payload(login_id="user123", email="other@example.com"),
        )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "AUTH_LOGIN_ID_UNAVAILABLE"
    assert _user_count() == 1


def test_signup_rejects_a_case_insensitive_duplicate_email() -> None:
    with TestClient(app) as client:
        first = client.post("/api/v1/auth/signup", json=valid_payload())
        second = client.post(
            "/api/v1/auth/signup",
            json=valid_payload(login_id="Other123", email="user@EXAMPLE.com"),
        )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "AUTH_EMAIL_UNAVAILABLE"
    assert _user_count() == 1


def test_signup_rejects_a_future_birth_date() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/signup",
            json=valid_payload(birth_date="2999-01-01"),
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"
    assert response.json()["error"]["fields"][0]["field"] == "body.birth_date"
    assert _user_count() == 0


def _user_count() -> int:
    with SessionFactory() as session:
        return session.scalar(select(func.count()).select_from(User)) or 0
