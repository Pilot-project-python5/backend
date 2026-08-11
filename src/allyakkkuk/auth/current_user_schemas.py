"""현재 사용자·세션 상태 HTTP 응답 스키마."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from allyakkkuk.auth.models import Gender, UserStatus


class CurrentUserView(BaseModel):
    id: UUID
    login_id: str
    name: str
    email: EmailStr
    status: UserStatus
    email_verified_at: datetime
    birth_date: date
    gender: Gender
    height_cm: Decimal
    weight_kg: Decimal


class CurrentSessionView(BaseModel):
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "authenticated": True,
                    "user": {
                        "id": "11111111-1111-4111-8111-111111111111",
                        "login_id": "User123",
                        "name": "홍길동",
                        "email": "user@example.com",
                        "status": "ACTIVE",
                        "email_verified_at": "2026-08-11T09:00:00Z",
                        "birth_date": "1995-05-20",
                        "gender": "MALE",
                        "height_cm": "175.00",
                        "weight_kg": "70.00",
                    },
                    "session": {
                        "access_token_expires_at": "2026-08-11T09:15:00Z",
                        "refresh_token_expires_at": "2026-08-25T09:00:00Z",
                    },
                }
            ]
        }
    )

    authenticated: Literal[True] = True
    user: CurrentUserView
    session: CurrentSessionView
