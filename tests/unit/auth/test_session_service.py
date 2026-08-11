from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from allyakkkuk.auth.models import UserStatus
from allyakkkuk.auth.session_repository import (
    RefreshSessionRecord,
    SessionPersistenceError,
    SessionRepository,
)
from allyakkkuk.auth.session_service import SessionService
from allyakkkuk.auth.tokens import (
    IssuedSessionTokens,
    RefreshTokenParts,
    SessionTokenRotator,
)
from allyakkkuk.core.errors import AppError
from allyakkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-1.3")]

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
SESSION_ID = UUID("22222222-2222-4222-8222-222222222222")
VALID_TOKEN = f"{SESSION_ID}.{'a' * 64}"
REUSED_TOKEN = f"{SESSION_ID}.{'b' * 64}"
UNKNOWN_TOKEN = "33333333-3333-4333-8333-333333333333." + "a" * 64


class FixedTokenRotator(SessionTokenRotator):
    def __init__(self) -> None:
        self.rotations: list[tuple[UUID, UUID, datetime, datetime]] = []

    def parse_refresh_token(self, raw_token: str | None) -> RefreshTokenParts | None:
        if raw_token not in {VALID_TOKEN, REUSED_TOKEN, UNKNOWN_TOKEN}:
            return None
        selector, secret = raw_token.split(".")
        return RefreshTokenParts(session_id=UUID(selector), secret=secret)

    def verify_refresh_token(
        self,
        session_id: UUID,
        refresh_token: str,
        expected_hash: str,
    ) -> bool:
        return (
            session_id == SESSION_ID
            and refresh_token == VALID_TOKEN
            and expected_hash == "stored-token-hash"
        )

    def rotate(
        self,
        user_id: UUID,
        session_id: UUID,
        issued_at: datetime,
        refresh_token_expires_at: datetime,
    ) -> IssuedSessionTokens:
        self.rotations.append(
            (user_id, session_id, issued_at, refresh_token_expires_at)
        )
        return IssuedSessionTokens(
            access_token="new-access-token",
            refresh_token=f"{session_id}.{'c' * 64}",
            refresh_token_hash="new-token-hash",
            access_token_expires_at=issued_at + timedelta(minutes=15),
            refresh_token_expires_at=refresh_token_expires_at,
        )


class FakeSessionRepository(SessionRepository):
    def __init__(
        self,
        record: RefreshSessionRecord | None,
        *,
        fail_lookup: bool = False,
        fail_rotate: bool = False,
        fail_revoke: bool = False,
    ) -> None:
        self.record = record
        self.fail_lookup = fail_lookup
        self.fail_rotate = fail_rotate
        self.fail_revoke = fail_revoke
        self.lookups: list[UUID] = []
        self.rotations: list[tuple[UUID, str, datetime]] = []
        self.revocations: list[tuple[UUID, datetime]] = []
        self.rollbacks = 0

    def get_for_update(self, session_id: UUID) -> RefreshSessionRecord | None:
        self.lookups.append(session_id)
        if self.fail_lookup:
            raise SessionPersistenceError
        return self.record

    def rotate(
        self,
        session_id: UUID,
        token_hash: str,
        last_used_at: datetime,
    ) -> None:
        if self.fail_rotate:
            raise SessionPersistenceError
        self.rotations.append((session_id, token_hash, last_used_at))

    def revoke(self, session_id: UUID, revoked_at: datetime) -> None:
        if self.fail_revoke:
            raise SessionPersistenceError
        self.revocations.append((session_id, revoked_at))

    def rollback(self) -> None:
        self.rollbacks += 1


def active_session(**overrides: object) -> RefreshSessionRecord:
    values: dict[str, object] = {
        "id": SESSION_ID,
        "user_id": USER_ID,
        "token_hash": "stored-token-hash",
        "expires_at": NOW + timedelta(days=1),
        "revoked_at": None,
        "last_used_at": None,
        "user_status": UserStatus.ACTIVE,
        "email_verified_at": NOW - timedelta(days=1),
    }
    values.update(overrides)
    return RefreshSessionRecord(**values)  # type: ignore[arg-type]


def build_service(
    repository: FakeSessionRepository,
) -> tuple[SessionService, FixedTokenRotator]:
    tokens = FixedTokenRotator()
    return (
        SessionService(
            repository=repository,
            token_rotator=tokens,
            clock=FakeClock(NOW),
        ),
        tokens,
    )


def assert_invalid_session(captured: pytest.ExceptionInfo[AppError]) -> None:
    assert captured.value.status_code == 401
    assert captured.value.code == "AUTH_SESSION_INVALID"
    assert captured.value.message == "유효하지 않은 인증 세션입니다."


def test_refresh_rotates_same_session_and_preserves_expiration() -> None:
    repository = FakeSessionRepository(active_session())
    service, tokens = build_service(repository)

    result = service.refresh(VALID_TOKEN)

    assert result.authenticated_at == NOW
    assert result.access_token == "new-access-token"
    assert result.refresh_token_expires_at == NOW + timedelta(days=1)
    assert tokens.rotations == [(USER_ID, SESSION_ID, NOW, NOW + timedelta(days=1))]
    assert repository.rotations == [(SESSION_ID, "new-token-hash", NOW)]
    assert repository.revocations == []


@pytest.mark.parametrize(
    ("raw_token", "record"),
    [
        (None, active_session()),
        ("malformed", active_session()),
        (UNKNOWN_TOKEN, None),
        (VALID_TOKEN, active_session(expires_at=NOW)),
        (VALID_TOKEN, active_session(revoked_at=NOW - timedelta(minutes=1))),
    ],
)
def test_refresh_rejects_invalid_session_reasons_with_same_error(
    raw_token: str | None,
    record: RefreshSessionRecord | None,
) -> None:
    repository = FakeSessionRepository(record)
    service, _ = build_service(repository)

    with pytest.raises(AppError) as captured:
        service.refresh(raw_token)

    assert_invalid_session(captured)
    assert repository.rotations == []
    assert repository.revocations == []


def test_reused_refresh_token_revokes_session() -> None:
    repository = FakeSessionRepository(active_session())
    service, _ = build_service(repository)

    with pytest.raises(AppError) as captured:
        service.refresh(REUSED_TOKEN)

    assert_invalid_session(captured)
    assert repository.revocations == [(SESSION_ID, NOW)]
    assert repository.rotations == []


@pytest.mark.parametrize(
    ("status", "verified_at"),
    [
        (UserStatus.PENDING_EMAIL_VERIFICATION, None),
        (UserStatus.ACTIVE, None),
        (UserStatus.SUSPENDED, NOW),
    ],
)
def test_refresh_revokes_ineligible_account_session(
    status: UserStatus,
    verified_at: datetime | None,
) -> None:
    repository = FakeSessionRepository(
        active_session(user_status=status, email_verified_at=verified_at)
    )
    service, _ = build_service(repository)

    with pytest.raises(AppError) as captured:
        service.refresh(VALID_TOKEN)

    assert_invalid_session(captured)
    assert repository.revocations == [(SESSION_ID, NOW)]


@pytest.mark.parametrize("failure", ["lookup", "rotate", "revoke"])
def test_refresh_database_failure_is_hidden(failure: str) -> None:
    repository = FakeSessionRepository(
        active_session(),
        fail_lookup=failure == "lookup",
        fail_rotate=failure == "rotate",
        fail_revoke=failure == "revoke",
    )
    service, _ = build_service(repository)
    token = REUSED_TOKEN if failure == "revoke" else VALID_TOKEN

    with pytest.raises(AppError) as captured:
        service.refresh(token)

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"
    assert repository.rollbacks == 1


def test_logout_revokes_only_matching_active_session() -> None:
    repository = FakeSessionRepository(active_session())
    service, _ = build_service(repository)

    service.logout(VALID_TOKEN)

    assert repository.revocations == [(SESSION_ID, NOW)]


@pytest.mark.parametrize(
    ("raw_token", "record"),
    [
        (None, active_session()),
        ("malformed", active_session()),
        (UNKNOWN_TOKEN, None),
        (VALID_TOKEN, active_session(expires_at=NOW)),
        (VALID_TOKEN, active_session(revoked_at=NOW)),
        (REUSED_TOKEN, active_session()),
    ],
)
def test_logout_is_idempotent_and_does_not_revoke_hash_mismatch(
    raw_token: str | None,
    record: RefreshSessionRecord | None,
) -> None:
    repository = FakeSessionRepository(record)
    service, _ = build_service(repository)

    service.logout(raw_token)

    assert repository.revocations == []


@pytest.mark.parametrize("failure", ["lookup", "revoke"])
def test_logout_database_failure_is_hidden(failure: str) -> None:
    repository = FakeSessionRepository(
        active_session(),
        fail_lookup=failure == "lookup",
        fail_revoke=failure == "revoke",
    )
    service, _ = build_service(repository)

    with pytest.raises(AppError) as captured:
        service.logout(VALID_TOKEN)

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"
    assert repository.rollbacks == 1
