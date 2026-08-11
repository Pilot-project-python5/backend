"""refresh session 회전·폐기를 위한 저장소 포트와 SQLAlchemy 구현."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.auth.models import RefreshSession, User, UserStatus


class SessionPersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class RefreshSessionRecord:
    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None
    user_status: UserStatus
    email_verified_at: datetime | None


class SessionRepository(Protocol):
    def get_for_update(self, session_id: UUID) -> RefreshSessionRecord | None: ...

    def rotate(
        self,
        session_id: UUID,
        token_hash: str,
        last_used_at: datetime,
    ) -> None: ...

    def revoke(self, session_id: UUID, revoked_at: datetime) -> None: ...

    def rollback(self) -> None: ...


class SQLAlchemySessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_update(self, session_id: UUID) -> RefreshSessionRecord | None:
        try:
            row = self._session.execute(
                select(RefreshSession, User)
                .join(User, User.id == RefreshSession.user_id)
                .where(RefreshSession.id == session_id)
                .with_for_update()
            ).one_or_none()
        except SQLAlchemyError as exc:
            raise SessionPersistenceError from exc
        if row is None:
            return None
        refresh_session, user = row
        return RefreshSessionRecord(
            id=refresh_session.id,
            user_id=refresh_session.user_id,
            token_hash=refresh_session.token_hash,
            expires_at=refresh_session.expires_at,
            revoked_at=refresh_session.revoked_at,
            last_used_at=refresh_session.last_used_at,
            user_status=UserStatus(user.status),
            email_verified_at=user.email_verified_at,
        )

    def rotate(
        self,
        session_id: UUID,
        token_hash: str,
        last_used_at: datetime,
    ) -> None:
        try:
            self._session.execute(
                update(RefreshSession)
                .where(
                    RefreshSession.id == session_id,
                    RefreshSession.revoked_at.is_(None),
                )
                .values(token_hash=token_hash, last_used_at=last_used_at)
            )
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise SessionPersistenceError from exc

    def revoke(self, session_id: UUID, revoked_at: datetime) -> None:
        try:
            self._session.execute(
                update(RefreshSession)
                .where(
                    RefreshSession.id == session_id,
                    RefreshSession.revoked_at.is_(None),
                )
                .values(revoked_at=revoked_at)
            )
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise SessionPersistenceError from exc

    def rollback(self) -> None:
        self._session.rollback()
