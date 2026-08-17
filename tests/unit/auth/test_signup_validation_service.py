from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from yeongyangkkuk.auth.repository import (
    SignupValidationConflicts,
    SignupValidationPersistenceError,
)
from yeongyangkkuk.auth.service import (
    SignupValidationCommand,
    SignupValidationService,
)
from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-1.1.2")]


class FakeSignupValidationRepository:
    def __init__(
        self,
        *,
        conflicts: SignupValidationConflicts | None = None,
        fails: bool = False,
    ) -> None:
        self.conflicts = conflicts or SignupValidationConflicts(
            login_id_exists=False,
            email_exists=False,
        )
        self.fails = fails
        self.normalized_login_id: str | None = None
        self.normalized_email: str | None = None

    def find_conflicts(
        self,
        normalized_login_id: str,
        normalized_email: str,
    ) -> SignupValidationConflicts:
        self.normalized_login_id = normalized_login_id
        self.normalized_email = normalized_email
        if self.fails:
            raise SignupValidationPersistenceError
        return self.conflicts


def command(*, birth_date: date = date(1995, 5, 20)) -> SignupValidationCommand:
    return SignupValidationCommand(
        login_id="User123",
        email="User@Example.COM",
        birth_date=birth_date,
    )


def service(repository: FakeSignupValidationRepository) -> SignupValidationService:
    clock = FakeClock(datetime(2026, 8, 11, 9, 0, tzinfo=UTC))
    return SignupValidationService(repository=repository, clock=clock)


def test_signup_validation_returns_true_for_available_information() -> None:
    repository = FakeSignupValidationRepository()

    result = service(repository).validate(command())

    assert result.valid is True
    assert result.issues == ()
    assert repository.normalized_login_id == "user123"
    assert repository.normalized_email == "user@example.com"


def test_signup_validation_aggregates_conflicts_and_future_birth_date() -> None:
    repository = FakeSignupValidationRepository(
        conflicts=SignupValidationConflicts(
            login_id_exists=True,
            email_exists=True,
        )
    )

    result = service(repository).validate(command(birth_date=date(2026, 8, 12)))

    assert result.valid is False
    assert [(issue.field, issue.code) for issue in result.issues] == [
        ("login_id", "AUTH_LOGIN_ID_UNAVAILABLE"),
        ("email", "AUTH_EMAIL_UNAVAILABLE"),
        ("birth_date", "birth_date_future"),
    ]


def test_signup_validation_converts_database_failure() -> None:
    repository = FakeSignupValidationRepository(fails=True)

    with pytest.raises(AppError) as captured:
        service(repository).validate(command())

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"
