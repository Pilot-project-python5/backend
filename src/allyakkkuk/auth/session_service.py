"""리프레시 회전과 현재 기기 로그아웃 애플리케이션 서비스."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from allyakkkuk.auth.models import UserStatus
from allyakkkuk.auth.session_repository import (
    SessionPersistenceError,
    SessionRepository,
)
from allyakkkuk.auth.tokens import SessionTokenRotator
from allyakkkuk.core.errors import AppError
from allyakkkuk.ports.clock import Clock


@dataclass(frozen=True, slots=True)
class SessionRefreshResult:
    authenticated_at: datetime
    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


class SessionService:
    def __init__(
        self,
        *,
        repository: SessionRepository,
        token_rotator: SessionTokenRotator,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._token_rotator = token_rotator
        self._clock = clock

    def refresh(self, raw_token: str | None) -> SessionRefreshResult:
        parts = self._token_rotator.parse_refresh_token(raw_token)
        if parts is None or raw_token is None:
            raise _invalid_session()

        now = self._clock.now()
        try:
            session = self._repository.get_for_update(parts.session_id)
        except SessionPersistenceError as exc:
            self._repository.rollback()
            raise _service_unavailable() from exc

        if (
            session is None
            or session.revoked_at is not None
            or now >= session.expires_at
        ):
            self._repository.rollback()
            raise _invalid_session()

        if not self._token_rotator.verify_refresh_token(
            session.id,
            raw_token,
            session.token_hash,
        ):
            self._revoke_or_unavailable(session.id, now)
            raise _invalid_session()

        if (
            session.user_status != UserStatus.ACTIVE
            or session.email_verified_at is None
        ):
            self._revoke_or_unavailable(session.id, now)
            raise _invalid_session()

        tokens = self._token_rotator.rotate(
            session.user_id,
            session.id,
            now,
            session.expires_at,
        )
        try:
            self._repository.rotate(
                session.id,
                tokens.refresh_token_hash,
                now,
            )
        except SessionPersistenceError as exc:
            self._repository.rollback()
            raise _service_unavailable() from exc

        return SessionRefreshResult(
            authenticated_at=now,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            access_token_expires_at=tokens.access_token_expires_at,
            refresh_token_expires_at=tokens.refresh_token_expires_at,
        )

    def logout(self, raw_token: str | None) -> None:
        parts = self._token_rotator.parse_refresh_token(raw_token)
        if parts is None or raw_token is None:
            return

        now = self._clock.now()
        try:
            session = self._repository.get_for_update(parts.session_id)
        except SessionPersistenceError as exc:
            self._repository.rollback()
            raise _service_unavailable() from exc

        if (
            session is None
            or session.revoked_at is not None
            or now >= session.expires_at
            or not self._token_rotator.verify_refresh_token(
                session.id,
                raw_token,
                session.token_hash,
            )
        ):
            self._repository.rollback()
            return

        self._revoke_or_unavailable(session.id, now)

    def _revoke_or_unavailable(self, session_id: UUID, revoked_at: datetime) -> None:
        try:
            self._repository.revoke(session_id, revoked_at)
        except SessionPersistenceError as exc:
            self._repository.rollback()
            raise _service_unavailable() from exc


def _invalid_session() -> AppError:
    return AppError(
        status_code=401,
        code="AUTH_SESSION_INVALID",
        message="유효하지 않은 인증 세션입니다.",
    )


def _service_unavailable() -> AppError:
    return AppError(
        status_code=503,
        code="SERVICE_UNAVAILABLE",
        message="서비스가 아직 준비되지 않았습니다.",
    )
