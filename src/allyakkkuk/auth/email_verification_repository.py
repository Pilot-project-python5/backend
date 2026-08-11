"""이메일 인증 저장소 포트와 SQLAlchemy 구현."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.auth.models import EmailVerification, User, UserStatus


class EmailVerificationPersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class EmailVerificationUserRecord:
    id: UUID
    email: str
    status: UserStatus
    email_verified_at: datetime | None


@dataclass(frozen=True, slots=True)
class EmailVerificationRecord:
    id: UUID
    user_id: UUID
    purpose: str
    code_hash: str
    expires_at: datetime
    resend_available_at: datetime
    failed_attempts: int
    used_at: datetime | None
    superseded_at: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EmailVerificationCreateData:
    id: UUID
    user_id: UUID
    purpose: str
    code_hash: str
    expires_at: datetime
    resend_available_at: datetime
    created_at: datetime


class EmailVerificationRepository(Protocol):
    def find_user_id(self, verification_id: UUID) -> UUID | None: ...

    def get_user_for_update(
        self, user_id: UUID
    ) -> EmailVerificationUserRecord | None: ...

    def get_latest_for_update(
        self, user_id: UUID
    ) -> EmailVerificationRecord | None: ...

    def get_for_update(
        self, verification_id: UUID
    ) -> EmailVerificationRecord | None: ...

    def supersede(self, verification_id: UUID, superseded_at: datetime) -> None: ...

    def add(self, data: EmailVerificationCreateData) -> None: ...

    def set_failed_attempts(self, verification_id: UUID, attempts: int) -> None: ...

    def complete(
        self, verification_id: UUID, user_id: UUID, completed_at: datetime
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class SQLAlchemyEmailVerificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_user_id(self, verification_id: UUID) -> UUID | None:
        try:
            return self._session.scalar(
                select(EmailVerification.user_id).where(
                    EmailVerification.id == verification_id
                )
            )
        except SQLAlchemyError as exc:
            raise EmailVerificationPersistenceError from exc

    def get_user_for_update(self, user_id: UUID) -> EmailVerificationUserRecord | None:
        try:
            user = self._session.scalar(
                select(User).where(User.id == user_id).with_for_update()
            )
        except SQLAlchemyError as exc:
            raise EmailVerificationPersistenceError from exc
        if user is None:
            return None
        return EmailVerificationUserRecord(
            id=user.id,
            email=user.email,
            status=UserStatus(user.status),
            email_verified_at=user.email_verified_at,
        )

    def get_latest_for_update(self, user_id: UUID) -> EmailVerificationRecord | None:
        try:
            verification = self._session.scalar(
                select(EmailVerification)
                .where(EmailVerification.user_id == user_id)
                .order_by(
                    EmailVerification.created_at.desc(),
                    EmailVerification.id.desc(),
                )
                .limit(1)
                .with_for_update()
            )
        except SQLAlchemyError as exc:
            raise EmailVerificationPersistenceError from exc
        return _to_record(verification)

    def get_for_update(self, verification_id: UUID) -> EmailVerificationRecord | None:
        try:
            verification = self._session.scalar(
                select(EmailVerification)
                .where(EmailVerification.id == verification_id)
                .with_for_update()
            )
        except SQLAlchemyError as exc:
            raise EmailVerificationPersistenceError from exc
        return _to_record(verification)

    def supersede(self, verification_id: UUID, superseded_at: datetime) -> None:
        try:
            self._session.execute(
                update(EmailVerification)
                .where(
                    EmailVerification.id == verification_id,
                    EmailVerification.used_at.is_(None),
                    EmailVerification.superseded_at.is_(None),
                )
                .values(superseded_at=superseded_at)
            )
        except SQLAlchemyError as exc:
            raise EmailVerificationPersistenceError from exc

    def add(self, data: EmailVerificationCreateData) -> None:
        verification = EmailVerification(
            id=data.id,
            user_id=data.user_id,
            purpose=data.purpose,
            code_hash=data.code_hash,
            expires_at=data.expires_at,
            resend_available_at=data.resend_available_at,
            failed_attempts=0,
            used_at=None,
            superseded_at=None,
            created_at=data.created_at,
        )
        try:
            self._session.add(verification)
            self._session.flush()
        except SQLAlchemyError as exc:
            raise EmailVerificationPersistenceError from exc

    def set_failed_attempts(self, verification_id: UUID, attempts: int) -> None:
        try:
            self._session.execute(
                update(EmailVerification)
                .where(EmailVerification.id == verification_id)
                .values(failed_attempts=attempts)
            )
        except SQLAlchemyError as exc:
            raise EmailVerificationPersistenceError from exc

    def complete(
        self, verification_id: UUID, user_id: UUID, completed_at: datetime
    ) -> None:
        try:
            self._session.execute(
                update(EmailVerification)
                .where(EmailVerification.id == verification_id)
                .values(used_at=completed_at)
            )
            self._session.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    status=UserStatus.ACTIVE.value,
                    email_verified_at=completed_at,
                    updated_at=completed_at,
                )
            )
        except SQLAlchemyError as exc:
            raise EmailVerificationPersistenceError from exc

    def commit(self) -> None:
        try:
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise EmailVerificationPersistenceError from exc

    def rollback(self) -> None:
        self._session.rollback()


def _to_record(
    verification: EmailVerification | None,
) -> EmailVerificationRecord | None:
    if verification is None:
        return None
    return EmailVerificationRecord(
        id=verification.id,
        user_id=verification.user_id,
        purpose=verification.purpose,
        code_hash=verification.code_hash,
        expires_at=verification.expires_at,
        resend_available_at=verification.resend_available_at,
        failed_attempts=verification.failed_attempts,
        used_at=verification.used_at,
        superseded_at=verification.superseded_at,
        created_at=verification.created_at,
    )
