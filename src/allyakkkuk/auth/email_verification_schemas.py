"""이메일 인증 HTTP 요청·응답 스키마."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from allyakkkuk.auth.models import UserStatus

VerificationCodeField = Annotated[str, Field(pattern=r"^[0-9]{6}$")]


class EmailVerificationIssueRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"user_id": "11111111-1111-4111-8111-111111111111"}]
        }
    )

    user_id: UUID


class EmailVerificationIssueResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "verification_id": "22222222-2222-4222-8222-222222222222",
                    "expires_at": "2026-08-11T09:10:00Z",
                    "resend_available_at": "2026-08-11T09:01:00Z",
                }
            ]
        }
    )

    verification_id: UUID
    expires_at: datetime
    resend_available_at: datetime


class EmailVerificationConfirmRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "verification_id": "22222222-2222-4222-8222-222222222222",
                    "code": "123456",
                }
            ]
        }
    )

    verification_id: UUID
    code: VerificationCodeField


class EmailVerificationConfirmResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": "11111111-1111-4111-8111-111111111111",
                    "status": "ACTIVE",
                    "email_verified_at": "2026-08-11T09:00:00Z",
                }
            ]
        }
    )

    user_id: UUID
    status: UserStatus
    email_verified_at: datetime
