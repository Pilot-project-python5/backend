"""화면 알림 HTTP 응답 스키마."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

NotificationType = Literal["REPURCHASE", "EXPIRATION"]


class NotificationListItemResponse(BaseModel):
    id: UUID
    care_item_id: UUID
    product_name: str
    notification_type: NotificationType
    reference_date: date
    trigger_days_before: Literal[5, 3, 1]
    scheduled_at: datetime
    created_at: datetime
    read_at: datetime | None
    is_read: bool


class NotificationListResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": "41000000-0000-4000-8000-000000000001",
                            "care_item_id": ("31000000-0000-4000-8000-000000000001"),
                            "product_name": "라이프익스텐션 투퍼데이",
                            "notification_type": "REPURCHASE",
                            "reference_date": "2026-08-19",
                            "trigger_days_before": 5,
                            "scheduled_at": "2026-08-14T00:00:00Z",
                            "created_at": "2026-08-14T00:01:00Z",
                            "read_at": None,
                            "is_read": False,
                        }
                    ],
                    "page": 1,
                    "page_size": 20,
                    "total": 1,
                    "has_next": False,
                }
            ]
        }
    )

    items: list[NotificationListItemResponse]
    page: int
    page_size: int
    total: int
    has_next: bool


class NotificationReadResponse(BaseModel):
    id: UUID
    read_at: datetime
