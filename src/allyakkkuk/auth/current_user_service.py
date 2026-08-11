"""Access JWT와 서버 세션을 함께 검증하는 현재 사용자 서비스."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from allyakkkuk.auth.current_user_repository import (
    CurrentUserPersistenceError,
    CurrentUserRepository,
)
from allyakkkuk.auth.models import Gender, UserStatus
from allyakkkuk.auth.tokens import AccessTokenVerifier
from allyakkkuk.core.errors import AppError
from allyakkkuk.ports.clock import Clock


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    user_id: UUID
    login_id: str
    name: str
    email: str
    status: UserStatus
    email_verified_at: datetime
    birth_date: date
    gender: Gender
    height_cm: Decimal
    weight_kg: Decimal
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


class CurrentUserService:
    def __init__(
        self,
        *,
        repository: CurrentUserRepository,
        token_verifier: AccessTokenVerifier,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._token_verifier = token_verifier
        self._clock = clock

    def authenticate(self, raw_access_token: str | None) -> AuthenticatedUser:
        now = self._clock.now()
        claims = self._token_verifier.verify_access_token(raw_access_token, now)
        if claims is None:
            raise _auth_required()

        try:
            current = self._repository.get_current_user(
                claims.user_id,
                claims.session_id,
            )
        except CurrentUserPersistenceError as exc:
            raise _service_unavailable() from exc

        if (
            current is None
            or current.session_id != claims.session_id
            or current.status != UserStatus.ACTIVE
            or current.email_verified_at is None
            or current.session_revoked_at is not None
            or now >= current.session_expires_at
        ):
            raise _auth_required()

        return AuthenticatedUser(
            user_id=current.id,
            login_id=current.login_id,
            name=current.name,
            email=current.email,
            status=current.status,
            email_verified_at=current.email_verified_at,
            birth_date=current.birth_date,
            gender=current.gender,
            height_cm=current.height_cm,
            weight_kg=current.weight_kg,
            access_token_expires_at=claims.expires_at,
            refresh_token_expires_at=current.session_expires_at,
        )


def _auth_required() -> AppError:
    return AppError(
        status_code=401,
        code="AUTH_REQUIRED",
        message="인증이 필요합니다.",
    )


def _service_unavailable() -> AppError:
    return AppError(
        status_code=503,
        code="SERVICE_UNAVAILABLE",
        message="서비스가 아직 준비되지 않았습니다.",
    )
