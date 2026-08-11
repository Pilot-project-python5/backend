from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from allyakkkuk.auth.models import User
from allyakkkuk.db.session import SessionFactory
from allyakkkuk.main import app

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-1.1.2")]

_TEST_LOGIN_IDS = ("user123", "unreserved1")


@pytest.fixture(autouse=True)
def clean_test_users() -> Iterator[None]:
    _delete_test_users()
    yield
    _delete_test_users()


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


def test_valid_signup_information_returns_true_without_writing_data() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/signup/validation",
            json=valid_payload(),
        )

    assert response.status_code == 200
    assert response.json() == {"valid": True, "issues": []}
    assert "password" not in response.text
    assert _test_user_count() == 0


def test_validation_reports_login_id_and_email_conflicts_together() -> None:
    with TestClient(app) as client:
        created = client.post("/api/v1/auth/signup", json=valid_payload())
        response = client.post(
            "/api/v1/auth/signup/validation",
            json=valid_payload(login_id="uSER123", email="user@EXAMPLE.com"),
        )

    assert created.status_code == 201
    assert response.status_code == 200
    assert response.json() == {
        "valid": False,
        "issues": [
            {
                "field": "login_id",
                "code": "AUTH_LOGIN_ID_UNAVAILABLE",
                "message": "사용할 수 없는 아이디입니다.",
            },
            {
                "field": "email",
                "code": "AUTH_EMAIL_UNAVAILABLE",
                "message": "사용할 수 없는 이메일입니다.",
            },
        ],
    }
    assert _test_user_count() == 1


def test_signup_validation_does_not_reserve_identifiers() -> None:
    payload = valid_payload(login_id="Unreserved1", email="free@example.com")
    colliding_payload = valid_payload(
        login_id="unreserved1",
        email="other@example.com",
    )

    with TestClient(app) as client:
        validation = client.post(
            "/api/v1/auth/signup/validation",
            json=payload,
        )
        created = client.post("/api/v1/auth/signup", json=payload)
        collision = client.post("/api/v1/auth/signup", json=colliding_payload)

    assert validation.json() == {"valid": True, "issues": []}
    assert created.status_code == 201
    assert collision.status_code == 409
    assert collision.json()["error"]["code"] == "AUTH_LOGIN_ID_UNAVAILABLE"
    assert _test_user_count() == 1


def _delete_test_users() -> None:
    with SessionFactory.begin() as session:
        session.execute(
            delete(User).where(User.normalized_login_id.in_(_TEST_LOGIN_IDS))
        )


def _test_user_count() -> int:
    with SessionFactory() as session:
        statement = (
            select(func.count())
            .select_from(User)
            .where(User.normalized_login_id.in_(_TEST_LOGIN_IDS))
        )
        return session.scalar(statement) or 0
