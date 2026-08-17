from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from yeongyangkkuk.adapters.email import FakeEmailSender
from yeongyangkkuk.auth.email_verification import HmacVerificationCodeHasher
from yeongyangkkuk.auth.email_verification_repository import (
    SQLAlchemyEmailVerificationRepository,
)
from yeongyangkkuk.auth.email_verification_router import get_email_verification_service
from yeongyangkkuk.auth.email_verification_service import EmailVerificationService
from yeongyangkkuk.auth.models import EmailVerification, User
from yeongyangkkuk.db.session import SessionFactory, get_db_session
from yeongyangkkuk.main import app
from yeongyangkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-1.1.3")]

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)


class SequenceCodeGenerator:
    def __init__(self) -> None:
        self._codes = iter(("123456", "654321", "112233"))

    def generate(self) -> str:
        return next(self._codes)


@pytest.fixture
def created_login_ids() -> Iterator[list[str]]:
    login_ids: list[str] = []
    yield login_ids
    app.dependency_overrides.pop(get_email_verification_service, None)
    if login_ids:
        with SessionFactory.begin() as session:
            session.execute(delete(User).where(User.normalized_login_id.in_(login_ids)))


@pytest.fixture
def verification_dependencies() -> tuple[FakeClock, FakeEmailSender]:
    clock = FakeClock(NOW)
    sender = FakeEmailSender()
    generator = SequenceCodeGenerator()
    hasher = HmacVerificationCodeHasher("acceptance-test-secret")

    def override_service(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> EmailVerificationService:
        return EmailVerificationService(
            repository=SQLAlchemyEmailVerificationRepository(session),
            code_generator=generator,
            code_hasher=hasher,
            email_sender=sender,
            clock=clock,
        )

    app.dependency_overrides[get_email_verification_service] = override_service
    return clock, sender


def signup(client: TestClient, created_login_ids: list[str]) -> UUID:
    suffix = uuid4().hex[:8]
    login_id = f"Email{suffix}"
    created_login_ids.append(login_id.casefold())
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "이메일 인증",
            "login_id": login_id,
            "password": "Safe!Pass123",
            "password_confirmation": "Safe!Pass123",
            "email": f"verify-{suffix}@example.com",
            "birth_date": "1995-05-20",
            "gender": "MALE",
            "height_cm": 175,
            "weight_kg": 70,
        },
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


def sent_code(sender: FakeEmailSender, index: int = -1) -> str:
    match = re.search(r"(?<!\d)\d{6}(?!\d)", sender.messages[index].text_body)
    assert match is not None
    return match.group()


def test_issue_stores_hash_and_confirm_activates_user(
    verification_dependencies: tuple[FakeClock, FakeEmailSender],
    created_login_ids: list[str],
) -> None:
    _, sender = verification_dependencies
    with TestClient(app) as client:
        user_id = signup(client, created_login_ids)
        issued = client.post(
            "/api/v1/auth/email-verifications", json={"user_id": str(user_id)}
        )
        code = sent_code(sender)
        confirmed = client.post(
            "/api/v1/auth/email-verifications/confirm",
            json={"verification_id": issued.json()["verification_id"], "code": code},
        )

    assert issued.status_code == 201
    assert issued.json()["expires_at"] == "2026-08-11T09:10:00Z"
    assert issued.json()["resend_available_at"] == "2026-08-11T09:01:00Z"
    assert len(sender.messages) == 1
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "ACTIVE"

    with SessionFactory() as session:
        user = session.get(User, user_id)
        verification = session.get(
            EmailVerification, UUID(issued.json()["verification_id"])
        )
    assert user is not None and user.status == "ACTIVE"
    assert user.email_verified_at == NOW
    assert verification is not None and verification.used_at == NOW
    assert verification.code_hash != code
    assert code not in verification.code_hash
    assert sender.messages[0].recipients == (user.email,)


def test_resend_waits_sixty_seconds_and_supersedes_previous_code(
    verification_dependencies: tuple[FakeClock, FakeEmailSender],
    created_login_ids: list[str],
) -> None:
    clock, sender = verification_dependencies
    with TestClient(app) as client:
        user_id = signup(client, created_login_ids)
        first = client.post(
            "/api/v1/auth/email-verifications", json={"user_id": str(user_id)}
        )
        first_code = sent_code(sender)
        too_soon = client.post(
            "/api/v1/auth/email-verifications/resend",
            json={"user_id": str(user_id)},
        )
        clock.advance(timedelta(seconds=60))
        second = client.post(
            "/api/v1/auth/email-verifications/resend",
            json={"user_id": str(user_id)},
        )
        old_confirm = client.post(
            "/api/v1/auth/email-verifications/confirm",
            json={
                "verification_id": first.json()["verification_id"],
                "code": first_code,
            },
        )
        new_confirm = client.post(
            "/api/v1/auth/email-verifications/confirm",
            json={
                "verification_id": second.json()["verification_id"],
                "code": sent_code(sender),
            },
        )

    assert too_soon.status_code == 429
    assert too_soon.json()["error"]["code"] == "AUTH_VERIFICATION_RESEND_TOO_SOON"
    assert len(sender.messages) == 2
    assert second.status_code == 201
    assert old_confirm.status_code == 409
    assert old_confirm.json()["error"]["code"] == "AUTH_VERIFICATION_NOT_ACTIVE"
    assert new_confirm.status_code == 200


def test_fifth_failure_locks_code_but_new_code_can_be_requested(
    verification_dependencies: tuple[FakeClock, FakeEmailSender],
    created_login_ids: list[str],
) -> None:
    clock, sender = verification_dependencies
    with TestClient(app) as client:
        user_id = signup(client, created_login_ids)
        issued = client.post(
            "/api/v1/auth/email-verifications", json={"user_id": str(user_id)}
        )
        url = "/api/v1/auth/email-verifications/confirm"
        payload = {
            "verification_id": issued.json()["verification_id"],
            "code": "000000",
        }
        failures = [client.post(url, json=payload) for _ in range(5)]
        locked_correct = client.post(
            url,
            json={
                "verification_id": issued.json()["verification_id"],
                "code": sent_code(sender),
            },
        )
        clock.advance(timedelta(seconds=60))
        resent = client.post(
            "/api/v1/auth/email-verifications/resend",
            json={"user_id": str(user_id)},
        )

    assert [item.status_code for item in failures] == [400, 400, 400, 400, 429]
    assert locked_correct.status_code == 429
    assert resent.status_code == 201
    with SessionFactory() as session:
        latest = session.scalar(
            select(EmailVerification)
            .where(EmailVerification.user_id == user_id)
            .order_by(EmailVerification.created_at.desc())
        )
    assert latest is not None and latest.failed_attempts == 0


def test_verified_user_cannot_request_another_code(
    verification_dependencies: tuple[FakeClock, FakeEmailSender],
    created_login_ids: list[str],
) -> None:
    _, sender = verification_dependencies
    with TestClient(app) as client:
        user_id = signup(client, created_login_ids)
        issued = client.post(
            "/api/v1/auth/email-verifications", json={"user_id": str(user_id)}
        )
        client.post(
            "/api/v1/auth/email-verifications/confirm",
            json={
                "verification_id": issued.json()["verification_id"],
                "code": sent_code(sender),
            },
        )
        repeated = client.post(
            "/api/v1/auth/email-verifications", json={"user_id": str(user_id)}
        )

    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "AUTH_EMAIL_ALREADY_VERIFIED"
