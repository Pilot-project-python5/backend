from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from yeongyangkkuk.auth.current_user_repository import (
    CurrentUserPersistenceError,
    CurrentUserRecord,
    CurrentUserRepository,
)
from yeongyangkkuk.auth.current_user_service import CurrentUserService
from yeongyangkkuk.auth.models import Gender, UserStatus
from yeongyangkkuk.auth.tokens import AccessTokenClaims, AccessTokenVerifier
from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-1.4")]

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
SESSION_ID = UUID("22222222-2222-4222-8222-222222222222")
TOKEN_ID = UUID("33333333-3333-4333-8333-333333333333")
OTHER_SESSION_ID = UUID("44444444-4444-4444-8444-444444444444")


class FixedAccessTokenVerifier(AccessTokenVerifier):
    def verify_access_token(
        self, raw_token: str | None, verified_at: datetime
    ) -> AccessTokenClaims | None:
        assert verified_at == NOW
        if raw_token != "valid-access-token":
            return None
        return AccessTokenClaims(
            user_id=USER_ID,
            session_id=SESSION_ID,
            token_id=TOKEN_ID,
            issued_at=NOW - timedelta(minutes=5),
            expires_at=NOW + timedelta(minutes=10),
        )


class FakeCurrentUserRepository(CurrentUserRepository):
    def __init__(
        self,
        record: CurrentUserRecord | None,
        *,
        fail: bool = False,
    ) -> None:
        self.record = record
        self.fail = fail
        self.lookups: list[tuple[UUID, UUID]] = []

    def get_current_user(
        self, user_id: UUID, session_id: UUID
    ) -> CurrentUserRecord | None:
        self.lookups.append((user_id, session_id))
        if self.fail:
            raise CurrentUserPersistenceError
        return self.record


def active_record(**overrides: object) -> CurrentUserRecord:
    values: dict[str, object] = {
        "id": USER_ID,
        "login_id": "User123",
        "name": "홍길동",
        "email": "user@example.com",
        "status": UserStatus.ACTIVE,
        "email_verified_at": NOW - timedelta(days=1),
        "birth_date": date(1995, 5, 20),
        "gender": Gender.MALE,
        "height_cm": Decimal("175.00"),
        "weight_kg": Decimal("70.00"),
        "session_id": SESSION_ID,
        "session_expires_at": NOW + timedelta(days=10),
        "session_revoked_at": None,
    }
    values.update(overrides)
    return CurrentUserRecord(**values)  # type: ignore[arg-type]


def build_service(repository: FakeCurrentUserRepository) -> CurrentUserService:
    return CurrentUserService(
        repository=repository,
        token_verifier=FixedAccessTokenVerifier(),
        clock=FakeClock(NOW),
    )


def assert_auth_required(captured: pytest.ExceptionInfo[AppError]) -> None:
    assert captured.value.status_code == 401
    assert captured.value.code == "AUTH_REQUIRED"
    assert captured.value.message == "인증이 필요합니다."


def test_authenticate_returns_public_user_and_session_state() -> None:
    repository = FakeCurrentUserRepository(active_record())
    service = build_service(repository)

    result = service.authenticate("valid-access-token")

    assert result.user_id == USER_ID
    assert result.login_id == "User123"
    assert result.email == "user@example.com"
    assert result.birth_date == date(1995, 5, 20)
    assert result.height_cm == Decimal("175.00")
    assert result.access_token_expires_at == NOW + timedelta(minutes=10)
    assert result.refresh_token_expires_at == NOW + timedelta(days=10)
    assert repository.lookups == [(USER_ID, SESSION_ID)]


@pytest.mark.parametrize("raw_token", [None, "", "invalid-access-token"])
def test_invalid_access_token_is_rejected_before_database_lookup(
    raw_token: str | None,
) -> None:
    repository = FakeCurrentUserRepository(active_record())
    service = build_service(repository)

    with pytest.raises(AppError) as captured:
        service.authenticate(raw_token)

    assert_auth_required(captured)
    assert repository.lookups == []


@pytest.mark.parametrize(
    "record",
    [
        None,
        active_record(session_id=OTHER_SESSION_ID),
        active_record(session_revoked_at=NOW - timedelta(minutes=1)),
        active_record(session_expires_at=NOW),
        active_record(status=UserStatus.PENDING_EMAIL_VERIFICATION),
        active_record(status=UserStatus.SUSPENDED),
        active_record(email_verified_at=None),
    ],
)
def test_invalid_database_session_and_account_reasons_share_one_error(
    record: CurrentUserRecord | None,
) -> None:
    service = build_service(FakeCurrentUserRepository(record))

    with pytest.raises(AppError) as captured:
        service.authenticate("valid-access-token")

    assert_auth_required(captured)


def test_database_failure_is_service_unavailable() -> None:
    service = build_service(FakeCurrentUserRepository(active_record(), fail=True))

    with pytest.raises(AppError) as captured:
        service.authenticate("valid-access-token")

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"
