"""회원가입과 로그인 아이디 조회 저장소 포트·PostgreSQL 구현."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.auth.models import Gender, HealthProfile, User, UserStatus


class DuplicateLoginIdError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class SignupPersistenceError(Exception):
    pass


class LoginIdAvailabilityPersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class SignupData:
    name: str
    login_id: str
    normalized_login_id: str
    email: str
    normalized_email: str
    password_hash: str
    birth_date: date
    gender: Gender
    height_cm: Decimal
    weight_kg: Decimal
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SignupRecord:
    id: UUID
    login_id: str
    email: str
    status: UserStatus
    created_at: datetime


class SignupRepository(Protocol):
    def create(self, data: SignupData) -> SignupRecord: ...


class LoginIdAvailabilityRepository(Protocol):
    def exists(self, normalized_login_id: str) -> bool: ...


class SQLAlchemySignupRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, data: SignupData) -> SignupRecord:
        user_id = uuid4()
        user = User(
            id=user_id,
            name=data.name,
            login_id=data.login_id,
            normalized_login_id=data.normalized_login_id,
            email=data.email,
            normalized_email=data.normalized_email,
            password_hash=data.password_hash,
            email_verified_at=None,
            status=UserStatus.PENDING_EMAIL_VERIFICATION.value,
            created_at=data.created_at,
            updated_at=data.created_at,
        )
        profile = HealthProfile(
            user_id=user_id,
            birth_date=data.birth_date,
            gender=data.gender.value,
            height_cm=data.height_cm,
            weight_kg=data.weight_kg,
            created_at=data.created_at,
            updated_at=data.created_at,
        )
        try:
            self._session.add(user)
            self._session.flush()
            self._session.add(profile)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            constraint_name = _constraint_name(exc)
            if constraint_name == "uq_users_normalized_login_id":
                raise DuplicateLoginIdError from exc
            if constraint_name == "uq_users_normalized_email":
                raise DuplicateEmailError from exc
            raise SignupPersistenceError from exc
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise SignupPersistenceError from exc

        return SignupRecord(
            id=user.id,
            login_id=user.login_id,
            email=user.email,
            status=UserStatus(user.status),
            created_at=user.created_at,
        )


class SQLAlchemyLoginIdAvailabilityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def exists(self, normalized_login_id: str) -> bool:
        statement = (
            select(User.id)
            .where(User.normalized_login_id == normalized_login_id)
            .limit(1)
        )
        try:
            return self._session.scalar(statement) is not None
        except SQLAlchemyError as exc:
            raise LoginIdAvailabilityPersistenceError from exc


def _constraint_name(exc: IntegrityError) -> str | None:
    diagnostic = getattr(exc.orig, "diag", None)
    value = getattr(diagnostic, "constraint_name", None)
    return value if isinstance(value, str) else None
