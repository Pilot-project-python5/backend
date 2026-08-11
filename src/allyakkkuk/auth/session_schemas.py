"""세션 갱신 HTTP 응답 스키마."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionRefreshResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "authenticated_at": "2026-08-11T09:00:00Z",
                    "access_token_expires_at": "2026-08-11T09:15:00Z",
                    "refresh_token_expires_at": "2026-08-25T09:00:00Z",
                }
            ]
        }
    )

    authenticated_at: datetime
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
