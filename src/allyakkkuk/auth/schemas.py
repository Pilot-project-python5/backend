"""회원가입 HTTP 요청과 응답 스키마."""

from __future__ import annotations

import string
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    ValidationInfo,
    field_validator,
)

from allyakkkuk.auth.models import Gender, UserStatus

PasswordField = Annotated[SecretStr, Field(min_length=8, max_length=20)]
_ALLOWED_PASSWORD_CHARACTERS = frozenset(
    string.ascii_letters + string.digits + string.punctuation
)


class SignupRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "홍길동",
                    "login_id": "User123",
                    "password": "Safe!Pass123",
                    "password_confirmation": "Safe!Pass123",
                    "email": "user@example.com",
                    "birth_date": "1995-05-20",
                    "gender": "MALE",
                    "height_cm": 175,
                    "weight_kg": 70,
                }
            ]
        }
    )

    name: str = Field(min_length=1, max_length=50)
    login_id: str = Field(
        min_length=5,
        max_length=20,
        pattern=r"^[A-Za-z0-9]+$",
    )
    password: PasswordField
    password_confirmation: PasswordField
    email: EmailStr = Field(max_length=320)
    birth_date: date
    gender: Gender
    height_cm: Decimal = Field(ge=50, le=250, max_digits=5, decimal_places=2)
    weight_kg: Decimal = Field(ge=10, le=500, max_digits=6, decimal_places=2)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not 1 <= len(stripped) <= 50:
            raise ValueError("이름은 공백을 제외하고 1~50자여야 합니다.")
        return stripped

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if any(character not in _ALLOWED_PASSWORD_CHARACTERS for character in password):
            raise ValueError(
                "비밀번호는 영문자, 숫자와 ASCII 특수문자만 사용할 수 있습니다."
            )
        if not any(character in string.ascii_letters for character in password):
            raise ValueError("비밀번호에 영문자가 필요합니다.")
        if not any(character in string.digits for character in password):
            raise ValueError("비밀번호에 숫자가 필요합니다.")
        if not any(character in string.punctuation for character in password):
            raise ValueError("비밀번호에 특수문자가 필요합니다.")
        return value

    @field_validator("password_confirmation")
    @classmethod
    def validate_password_confirmation(
        cls, value: SecretStr, info: ValidationInfo
    ) -> SecretStr:
        password = info.data.get("password")
        if isinstance(password, SecretStr) and (
            value.get_secret_value() != password.get_secret_value()
        ):
            raise ValueError("비밀번호 확인이 일치하지 않습니다.")
        return value


class SignupResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "11111111-1111-4111-8111-111111111111",
                    "login_id": "User123",
                    "email": "user@example.com",
                    "status": "PENDING_EMAIL_VERIFICATION",
                    "email_verification_required": True,
                    "created_at": "2026-08-10T09:00:00Z",
                }
            ]
        }
    )

    id: UUID
    login_id: str
    email: EmailStr
    status: UserStatus
    email_verification_required: bool = True
    created_at: datetime
