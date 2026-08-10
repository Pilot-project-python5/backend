"""회원가입 애플리케이션 서비스."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from allyakkkuk.auth.models import Gender, UserStatus
from allyakkkuk.auth.passwords import PasswordHasher
from allyakkkuk.auth.repository import (
    DuplicateEmailError,
    DuplicateLoginIdError,
    SignupData,
    SignupPersistenceError,
    SignupRepository,
)
from allyakkkuk.core.errors import AppError, ErrorFieldData
from allyakkkuk.ports.clock import Clock


@dataclass(frozen=True, slots=True)
class SignupCommand:
    name: str
    login_id: str
    password: str
    email: str
    birth_date: date
    gender: Gender
    height_cm: Decimal
    weight_kg: Decimal


@dataclass(frozen=True, slots=True)
class SignupResult:
    id: UUID
    login_id: str
    email: str
    status: UserStatus
    created_at: datetime


class SignupService:
    def __init__(
        self,
        repository: SignupRepository,
        password_hasher: PasswordHasher,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._clock = clock

    def signup(self, command: SignupCommand) -> SignupResult:
        now = self._clock.now()
        if command.birth_date > now.date():
            raise AppError(
                status_code=422,
                code="VALIDATION_FAILED",
                message="요청 값을 확인해주세요.",
                fields=(
                    ErrorFieldData(
                        field="body.birth_date",
                        code="birth_date_future",
                        message="생년월일은 미래일 수 없습니다.",
                    ),
                ),
            )

        data = SignupData(
            name=command.name.strip(),
            login_id=command.login_id,
            normalized_login_id=normalize_login_id(command.login_id),
            email=command.email.strip(),
            normalized_email=normalize_email(command.email),
            password_hash=self._password_hasher.hash(command.password),
            birth_date=command.birth_date,
            gender=command.gender,
            height_cm=command.height_cm,
            weight_kg=command.weight_kg,
            created_at=now,
        )
        try:
            record = self._repository.create(data)
        except DuplicateLoginIdError as exc:
            raise AppError(
                status_code=409,
                code="AUTH_LOGIN_ID_UNAVAILABLE",
                message="사용할 수 없는 아이디입니다.",
            ) from exc
        except DuplicateEmailError as exc:
            raise AppError(
                status_code=409,
                code="AUTH_EMAIL_UNAVAILABLE",
                message="사용할 수 없는 이메일입니다.",
            ) from exc
        except SignupPersistenceError as exc:
            raise AppError(
                status_code=503,
                code="SERVICE_UNAVAILABLE",
                message="서비스가 아직 준비되지 않았습니다.",
            ) from exc

        return SignupResult(
            id=record.id,
            login_id=record.login_id,
            email=record.email,
            status=record.status,
            created_at=record.created_at,
        )


def normalize_login_id(login_id: str) -> str:
    return login_id.strip().casefold()


def normalize_email(email: str) -> str:
    return email.strip().casefold()
