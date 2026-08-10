from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from allyakkkuk.auth.models import HealthProfile, User
from allyakkkuk.db.session import SessionFactory
from allyakkkuk.main import app

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-1.1.1")]


@pytest.fixture(autouse=True)
def clean_auth_tables() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(HealthProfile))
        session.execute(delete(User))
    yield
    with SessionFactory.begin() as session:
        session.execute(delete(HealthProfile))
        session.execute(delete(User))


def signup_payload() -> dict[str, object]:
    return {
        "name": "홍길동",
        "login_id": "Existing1",
        "password": "Safe!Pass123",
        "password_confirmation": "Safe!Pass123",
        "email": "existing@example.com",
        "birth_date": "1995-05-20",
        "gender": "MALE",
        "height_cm": 175,
        "weight_kg": 70,
    }


def test_available_login_id_returns_true_without_writing_data() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/auth/login-id/availability",
            params={"login_id": "Available1"},
        )

    assert response.status_code == 200
    assert response.json() == {"login_id": "Available1", "available": True}
    assert _user_count() == 0


def test_existing_login_id_is_unavailable_case_insensitively() -> None:
    with TestClient(app) as client:
        created = client.post("/api/v1/auth/signup", json=signup_payload())
        response = client.get(
            "/api/v1/auth/login-id/availability",
            params={"login_id": "eXISTING1"},
        )

    assert created.status_code == 201
    assert response.status_code == 200
    assert response.json() == {"login_id": "eXISTING1", "available": False}
    assert _user_count() == 1


def test_availability_check_does_not_reserve_the_login_id() -> None:
    payload = signup_payload()
    payload["login_id"] = "Unreserved1"
    colliding_payload = signup_payload()
    colliding_payload["login_id"] = "unreserved1"
    colliding_payload["email"] = "colliding@example.com"

    with TestClient(app) as client:
        before = client.get(
            "/api/v1/auth/login-id/availability",
            params={"login_id": "Unreserved1"},
        )
        created = client.post("/api/v1/auth/signup", json=payload)
        collision = client.post("/api/v1/auth/signup", json=colliding_payload)
        after = client.get(
            "/api/v1/auth/login-id/availability",
            params={"login_id": "UNRESERVED1"},
        )

    assert before.json()["available"] is True
    assert created.status_code == 201
    assert collision.status_code == 409
    assert collision.json()["error"]["code"] == "AUTH_LOGIN_ID_UNAVAILABLE"
    assert after.json()["available"] is False
    assert _user_count() == 1


def _user_count() -> int:
    with SessionFactory() as session:
        return session.scalar(select(func.count()).select_from(User)) or 0
