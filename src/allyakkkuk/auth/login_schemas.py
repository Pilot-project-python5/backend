"""로그인 요청·응답 HTTP 스키마."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, SecretStr

from allyakkkuk.auth.models import UserStatus
from allyakkkuk.auth.schemas import LoginIdField, PasswordField


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "login_id": "User123",
                    "password": "Safe!Pass123",
                }
            ]
        }
    )

    login_id: LoginIdField
    password: PasswordField


class LoginResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": "11111111-1111-4111-8111-111111111111",
                    "login_id": "User123",
                    "name": "홍길동",
                    "status": "ACTIVE",
                    "authenticated_at": "2026-08-11T09:00:00Z",
                    "access_token_expires_at": "2026-08-11T09:15:00Z",
                    "refresh_token_expires_at": "2026-08-25T09:00:00Z",
                }
            ]
        }
    )

    user_id: UUID
    login_id: str
    name: str
    status: UserStatus
    authenticated_at: datetime
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


def reveal_password(value: SecretStr) -> str:
    return value.get_secret_value()
