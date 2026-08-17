from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from yeongyangkkuk.auth.login_repository import (
    LoginPersistenceError,
    LoginRepository,
    LoginUserRecord,
    RefreshSessionCreateData,
)
from yeongyangkkuk.auth.login_service import LoginCommand, LoginService
from yeongyangkkuk.auth.models import UserStatus
from yeongyangkkuk.auth.tokens import IssuedSessionTokens, SessionTokenIssuer
from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-1.2")]

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)
USER_ID = UUID("11111111-1111-4111-8111-111111111111")


class RecordingPasswordHasher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def hash(self, password: str) -> str:
        return f"hash:{password}"

    def verify(self, password: str, encoded: str) -> bool:
        self.calls.append((password, encoded))
        return password == "Safe!Pass123" and encoded == "stored-password-hash"


class FixedTokenIssuer(SessionTokenIssuer):
    def issue(
        self, user_id: UUID, session_id: UUID, issued_at: datetime
    ) -> IssuedSessionTokens:
        return IssuedSessionTokens(
            access_token="access-token",
            refresh_token="refresh-token",
            refresh_token_hash="a" * 64,
            access_token_expires_at=issued_at + timedelta(minutes=15),
            refresh_token_expires_at=issued_at + timedelta(days=14),
        )


class FakeLoginRepository(LoginRepository):
    def __init__(
        self,
        user: LoginUserRecord | None,
        *,
        fail_lookup: bool = False,
        fail_create: bool = False,
    ) -> None:
        self.user = user
        self.fail_lookup = fail_lookup
        self.fail_create = fail_create
        self.normalized_login_id: str | None = None
        self.created: list[RefreshSessionCreateData] = []
        self.rollbacks = 0

    def get_user_for_update(self, normalized_login_id: str) -> LoginUserRecord | None:
        self.normalized_login_id = normalized_login_id
        if self.fail_lookup:
            raise LoginPersistenceError
        return self.user

    def create_refresh_session(self, data: RefreshSessionCreateData) -> None:
        if self.fail_create:
            raise LoginPersistenceError
        self.created.append(data)

    def rollback(self) -> None:
        self.rollbacks += 1


def active_user() -> LoginUserRecord:
    return LoginUserRecord(
        id=USER_ID,
        login_id="User123",
        name="홍길동",
        password_hash="stored-password-hash",
        status=UserStatus.ACTIVE,
        email_verified_at=NOW - timedelta(days=1),
    )


def build_service(
    repository: FakeLoginRepository,
    password_hasher: RecordingPasswordHasher,
) -> LoginService:
    return LoginService(
        repository=repository,
        password_hasher=password_hasher,
        dummy_password_hash="dummy-password-hash",
        token_issuer=FixedTokenIssuer(),
        clock=FakeClock(NOW),
    )


def command(*, password: str = "Safe!Pass123") -> LoginCommand:
    return LoginCommand(login_id="  USER123  ", password=password)


def test_active_user_login_normalizes_id_and_creates_session() -> None:
    repository = FakeLoginRepository(active_user())
    password_hasher = RecordingPasswordHasher()

    result = build_service(repository, password_hasher).login(command())

    assert repository.normalized_login_id == "user123"
    assert password_hasher.calls == [("Safe!Pass123", "stored-password-hash")]
    assert result.user_id == USER_ID
    assert result.status == UserStatus.ACTIVE
    assert result.access_token == "access-token"
    assert len(repository.created) == 1
    assert repository.created[0].token_hash == "a" * 64
    assert repository.created[0].created_at == NOW


def test_unknown_id_and_wrong_password_have_identical_public_error() -> None:
    missing_repository = FakeLoginRepository(None)
    missing_hasher = RecordingPasswordHasher()
    wrong_repository = FakeLoginRepository(active_user())
    wrong_hasher = RecordingPasswordHasher()

    with pytest.raises(AppError) as missing:
        build_service(missing_repository, missing_hasher).login(command())
    with pytest.raises(AppError) as wrong:
        build_service(wrong_repository, wrong_hasher).login(
            command(password="Wrong!Pass123")
        )

    assert (missing.value.status_code, missing.value.code, missing.value.message) == (
        wrong.value.status_code,
        wrong.value.code,
        wrong.value.message,
    )
    assert missing.value.status_code == 401
    assert missing.value.code == "AUTH_INVALID_CREDENTIALS"
    assert missing_hasher.calls == [("Safe!Pass123", "dummy-password-hash")]
    assert missing_repository.created == wrong_repository.created == []
    assert missing_repository.rollbacks == wrong_repository.rollbacks == 1


@pytest.mark.parametrize(
    ("status", "verified_at", "error_code"),
    [
        (UserStatus.PENDING_EMAIL_VERIFICATION, None, "AUTH_EMAIL_UNVERIFIED"),
        (UserStatus.ACTIVE, None, "AUTH_EMAIL_UNVERIFIED"),
        (UserStatus.SUSPENDED, NOW, "AUTH_ACCOUNT_SUSPENDED"),
    ],
)
def test_login_rejects_unverified_or_suspended_user(
    status: UserStatus,
    verified_at: datetime | None,
    error_code: str,
) -> None:
    user = active_user()
    repository = FakeLoginRepository(
        LoginUserRecord(
            id=user.id,
            login_id=user.login_id,
            name=user.name,
            password_hash=user.password_hash,
            status=status,
            email_verified_at=verified_at,
        )
    )

    with pytest.raises(AppError) as captured:
        build_service(repository, RecordingPasswordHasher()).login(command())

    assert captured.value.status_code == 403
    assert captured.value.code == error_code
    assert repository.created == []
    assert repository.rollbacks == 1


@pytest.mark.parametrize("failure", ["lookup", "create"])
def test_database_failure_is_hidden_and_does_not_return_tokens(failure: str) -> None:
    repository = FakeLoginRepository(
        active_user(),
        fail_lookup=failure == "lookup",
        fail_create=failure == "create",
    )

    with pytest.raises(AppError) as captured:
        build_service(repository, RecordingPasswordHasher()).login(command())

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"
    assert repository.created == []
    assert repository.rollbacks == 1
