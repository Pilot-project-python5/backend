from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from allyakkkuk.adapters.email import FakeEmailSender
from allyakkkuk.auth.email_verification import HmacVerificationCodeHasher
from allyakkkuk.auth.email_verification_repository import (
    EmailVerificationCreateData,
    EmailVerificationPersistenceError,
    EmailVerificationRecord,
    EmailVerificationRepository,
    EmailVerificationUserRecord,
)
from allyakkkuk.auth.email_verification_service import EmailVerificationService
from allyakkkuk.auth.models import UserStatus
from allyakkkuk.core.errors import AppError
from allyakkkuk.ports.clock import FakeClock
from allyakkkuk.ports.email import EmailDeliveryError, EmailSender, OutboundEmail

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-1.1.3")]

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
VERIFICATION_ID = UUID("22222222-2222-4222-8222-222222222222")


class FixedCodeGenerator:
    def generate(self) -> str:
        return "123456"


class FakeEmailVerificationRepository(EmailVerificationRepository):
    def __init__(self) -> None:
        self.user = EmailVerificationUserRecord(
            id=USER_ID,
            email="user@example.com",
            status=UserStatus.PENDING_EMAIL_VERIFICATION,
            email_verified_at=None,
        )
        self.verification: EmailVerificationRecord | None = None
        self.created: EmailVerificationCreateData | None = None
        self.commits = 0
        self.rollbacks = 0

    def find_user_id(self, verification_id: UUID) -> UUID | None:
        if self.verification and self.verification.id == verification_id:
            return self.verification.user_id
        return None

    def get_user_for_update(self, user_id: UUID) -> EmailVerificationUserRecord | None:
        return self.user if user_id == self.user.id else None

    def get_latest_for_update(self, user_id: UUID) -> EmailVerificationRecord | None:
        return self.verification if user_id == self.user.id else None

    def get_for_update(self, verification_id: UUID) -> EmailVerificationRecord | None:
        if self.verification and verification_id == self.verification.id:
            return self.verification
        return None

    def supersede(self, verification_id: UUID, superseded_at: datetime) -> None:
        assert self.verification is not None
        self.verification = replace(self.verification, superseded_at=superseded_at)

    def add(self, data: EmailVerificationCreateData) -> None:
        self.created = data
        self.verification = EmailVerificationRecord(
            id=data.id,
            user_id=data.user_id,
            purpose=data.purpose,
            code_hash=data.code_hash,
            expires_at=data.expires_at,
            resend_available_at=data.resend_available_at,
            failed_attempts=0,
            used_at=None,
            superseded_at=None,
            created_at=data.created_at,
        )

    def set_failed_attempts(self, verification_id: UUID, attempts: int) -> None:
        assert self.verification is not None
        self.verification = replace(self.verification, failed_attempts=attempts)

    def complete(
        self, verification_id: UUID, user_id: UUID, completed_at: datetime
    ) -> None:
        assert self.verification is not None
        self.verification = replace(self.verification, used_at=completed_at)
        self.user = replace(
            self.user,
            status=UserStatus.ACTIVE,
            email_verified_at=completed_at,
        )

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def build_service(
    repository: FakeEmailVerificationRepository,
    clock: FakeClock,
    email_sender: EmailSender | None = None,
) -> EmailVerificationService:
    return EmailVerificationService(
        repository=repository,
        code_generator=FixedCodeGenerator(),
        code_hasher=HmacVerificationCodeHasher("unit-test-secret"),
        email_sender=email_sender or FakeEmailSender(),
        clock=clock,
    )


def add_verification(repository: FakeEmailVerificationRepository) -> None:
    repository.verification = EmailVerificationRecord(
        id=VERIFICATION_ID,
        user_id=USER_ID,
        purpose="VERIFY_EMAIL",
        code_hash=HmacVerificationCodeHasher("unit-test-secret").hash(
            VERIFICATION_ID, "123456"
        ),
        expires_at=NOW + timedelta(minutes=10),
        resend_available_at=NOW + timedelta(seconds=60),
        failed_attempts=0,
        used_at=None,
        superseded_at=None,
        created_at=NOW,
    )


def test_code_expires_at_exactly_ten_minutes() -> None:
    repository = FakeEmailVerificationRepository()
    add_verification(repository)
    clock = FakeClock(NOW + timedelta(minutes=10))

    with pytest.raises(AppError) as captured:
        build_service(repository, clock).confirm(VERIFICATION_ID, "123456")

    assert captured.value.status_code == 410
    assert captured.value.code == "AUTH_VERIFICATION_EXPIRED"
    assert repository.user.status == UserStatus.PENDING_EMAIL_VERIFICATION


def test_resend_is_allowed_at_exactly_sixty_seconds_and_resets_attempts() -> None:
    repository = FakeEmailVerificationRepository()
    add_verification(repository)
    repository.set_failed_attempts(VERIFICATION_ID, 5)
    clock = FakeClock(NOW + timedelta(seconds=60))

    result = build_service(repository, clock).resend(USER_ID)

    assert result.verification_id != VERIFICATION_ID
    assert repository.created is not None
    assert repository.verification is not None
    assert repository.verification.failed_attempts == 0
    assert repository.commits == 1


def test_issue_rejects_before_resend_boundary() -> None:
    repository = FakeEmailVerificationRepository()
    add_verification(repository)
    clock = FakeClock(NOW + timedelta(seconds=59))

    with pytest.raises(AppError) as captured:
        build_service(repository, clock).issue(USER_ID)

    assert captured.value.status_code == 429
    assert captured.value.code == "AUTH_VERIFICATION_RESEND_TOO_SOON"


def test_suspended_user_cannot_request_a_code() -> None:
    repository = FakeEmailVerificationRepository()
    repository.user = replace(repository.user, status=UserStatus.SUSPENDED)
    clock = FakeClock(NOW)

    with pytest.raises(AppError) as captured:
        build_service(repository, clock).issue(USER_ID)

    assert captured.value.status_code == 409
    assert captured.value.code == "AUTH_VERIFICATION_NOT_ACTIVE"


class FailingEmailSender:
    def send(self, message: OutboundEmail) -> None:
        raise EmailDeliveryError


class FailingEmailVerificationRepository(FakeEmailVerificationRepository):
    def get_user_for_update(self, user_id: UUID) -> EmailVerificationUserRecord | None:
        raise EmailVerificationPersistenceError


def test_email_delivery_failure_rolls_back_issuance() -> None:
    repository = FakeEmailVerificationRepository()
    clock = FakeClock(NOW)

    with pytest.raises(AppError) as captured:
        build_service(repository, clock, FailingEmailSender()).issue(USER_ID)

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"
    assert repository.commits == 0
    assert repository.rollbacks == 1


def test_database_failure_is_hidden_as_service_unavailable() -> None:
    repository = FailingEmailVerificationRepository()
    clock = FakeClock(NOW)

    with pytest.raises(AppError) as captured:
        build_service(repository, clock).issue(USER_ID)

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"
    assert repository.rollbacks == 1


def test_hmac_hash_depends_on_verification_id_and_never_contains_code() -> None:
    hasher = HmacVerificationCodeHasher("unit-test-secret")
    other_id = UUID("33333333-3333-4333-8333-333333333333")

    first = hasher.hash(VERIFICATION_ID, "123456")
    second = hasher.hash(other_id, "123456")

    assert first != second
    assert "123456" not in first
    assert hasher.verify(VERIFICATION_ID, "123456", first) is True
    assert hasher.verify(VERIFICATION_ID, "654321", first) is False
