"""로그인 사용자 조회와 refresh session 저장소."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.auth.models import RefreshSession, User, UserStatus


class LoginPersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class LoginUserRecord:
    id: UUID
    login_id: str
    name: str
    password_hash: str
    status: UserStatus
    email_verified_at: datetime | None


@dataclass(frozen=True, slots=True)
class RefreshSessionCreateData:
    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    created_at: datetime


class LoginRepository(Protocol):
    def get_user_for_update(
        self, normalized_login_id: str
    ) -> LoginUserRecord | None: ...

    def create_refresh_session(self, data: RefreshSessionCreateData) -> None: ...

    def rollback(self) -> None: ...


class SQLAlchemyLoginRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_user_for_update(self, normalized_login_id: str) -> LoginUserRecord | None:
        try:
            user = self._session.scalar(
                select(User)
                .where(User.normalized_login_id == normalized_login_id)
                .with_for_update()
            )
        except SQLAlchemyError as exc:
            raise LoginPersistenceError from exc
        if user is None:
            return None
        return LoginUserRecord(
            id=user.id,
            login_id=user.login_id,
            name=user.name,
            password_hash=user.password_hash,
            status=UserStatus(user.status),
            email_verified_at=user.email_verified_at,
        )

    def create_refresh_session(self, data: RefreshSessionCreateData) -> None:
        session = RefreshSession(
            id=data.id,
            user_id=data.user_id,
            token_hash=data.token_hash,
            expires_at=data.expires_at,
            revoked_at=None,
            last_used_at=None,
            created_at=data.created_at,
        )
        try:
            self._session.add(session)
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise LoginPersistenceError from exc

    def rollback(self) -> None:
        self._session.rollback()
