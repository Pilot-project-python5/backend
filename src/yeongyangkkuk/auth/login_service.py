"""아이디·비밀번호 로그인 애플리케이션 서비스."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from yeongyangkkuk.auth.login_repository import (
    LoginPersistenceError,
    LoginRepository,
    RefreshSessionCreateData,
)
from yeongyangkkuk.auth.models import UserStatus
from yeongyangkkuk.auth.passwords import PasswordHasher
from yeongyangkkuk.auth.service import normalize_login_id
from yeongyangkkuk.auth.tokens import SessionTokenIssuer
from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.ports.clock import Clock


@dataclass(frozen=True, slots=True)
class LoginCommand:
    login_id: str
    password: str


@dataclass(frozen=True, slots=True)
class LoginResult:
    user_id: UUID
    login_id: str
    name: str
    status: UserStatus
    authenticated_at: datetime
    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


class LoginService:
    def __init__(
        self,
        *,
        repository: LoginRepository,
        password_hasher: PasswordHasher,
        dummy_password_hash: str,
        token_issuer: SessionTokenIssuer,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._dummy_password_hash = dummy_password_hash
        self._token_issuer = token_issuer
        self._clock = clock

    def login(self, command: LoginCommand) -> LoginResult:
        now = self._clock.now()
        try:
            user = self._repository.get_user_for_update(
                normalize_login_id(command.login_id)
            )
        except LoginPersistenceError as exc:
            self._repository.rollback()
            raise _service_unavailable() from exc

        if user is None:
            self._password_hasher.verify(command.password, self._dummy_password_hash)
            self._repository.rollback()
            raise _invalid_credentials()

        if not self._password_hasher.verify(command.password, user.password_hash):
            self._repository.rollback()
            raise _invalid_credentials()

        if user.status == UserStatus.SUSPENDED:
            self._repository.rollback()
            raise AppError(
                status_code=403,
                code="AUTH_ACCOUNT_SUSPENDED",
                message="정지된 계정입니다.",
            )
        if (
            user.status == UserStatus.PENDING_EMAIL_VERIFICATION
            or user.email_verified_at is None
        ):
            self._repository.rollback()
            raise AppError(
                status_code=403,
                code="AUTH_EMAIL_UNVERIFIED",
                message="이메일 인증이 필요합니다.",
            )

        session_id = uuid4()
        tokens = self._token_issuer.issue(user.id, session_id, now)
        try:
            self._repository.create_refresh_session(
                RefreshSessionCreateData(
                    id=session_id,
                    user_id=user.id,
                    token_hash=tokens.refresh_token_hash,
                    expires_at=tokens.refresh_token_expires_at,
                    created_at=now,
                )
            )
        except LoginPersistenceError as exc:
            self._repository.rollback()
            raise _service_unavailable() from exc

        return LoginResult(
            user_id=user.id,
            login_id=user.login_id,
            name=user.name,
            status=user.status,
            authenticated_at=now,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            access_token_expires_at=tokens.access_token_expires_at,
            refresh_token_expires_at=tokens.refresh_token_expires_at,
        )


def _invalid_credentials() -> AppError:
    return AppError(
        status_code=401,
        code="AUTH_INVALID_CREDENTIALS",
        message="아이디 또는 비밀번호가 올바르지 않습니다.",
    )


def _service_unavailable() -> AppError:
    return AppError(
        status_code=503,
        code="SERVICE_UNAVAILABLE",
        message="서비스가 아직 준비되지 않았습니다.",
    )
