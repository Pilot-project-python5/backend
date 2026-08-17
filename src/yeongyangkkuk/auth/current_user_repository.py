"""현재 사용자·건강 프로필·세션 상태 읽기 저장소."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from yeongyangkkuk.auth.models import (
    Gender,
    HealthProfile,
    RefreshSession,
    User,
    UserStatus,
)


class CurrentUserPersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class CurrentUserRecord:
    id: UUID
    login_id: str
    name: str
    email: str
    status: UserStatus
    email_verified_at: datetime | None
    birth_date: date
    gender: Gender
    height_cm: Decimal
    weight_kg: Decimal
    session_id: UUID
    session_expires_at: datetime
    session_revoked_at: datetime | None


class CurrentUserRepository(Protocol):
    def get_current_user(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> CurrentUserRecord | None: ...


class SQLAlchemyCurrentUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_current_user(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> CurrentUserRecord | None:
        try:
            row = self._session.execute(
                select(User, HealthProfile, RefreshSession)
                .join(HealthProfile, HealthProfile.user_id == User.id)
                .join(RefreshSession, RefreshSession.user_id == User.id)
                .where(
                    User.id == user_id,
                    RefreshSession.id == session_id,
                )
            ).one_or_none()
        except SQLAlchemyError as exc:
            raise CurrentUserPersistenceError from exc
        if row is None:
            return None
        user, profile, refresh_session = row
        return CurrentUserRecord(
            id=user.id,
            login_id=user.login_id,
            name=user.name,
            email=user.email,
            status=UserStatus(user.status),
            email_verified_at=user.email_verified_at,
            birth_date=profile.birth_date,
            gender=Gender(profile.gender),
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            session_id=refresh_session.id,
            session_expires_at=refresh_session.expires_at,
            session_revoked_at=refresh_session.revoked_at,
        )
