"""현재 사용자의 화면 알림 API."""

from __future__ import annotations

from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from allyakkkuk.api.schemas import ErrorResponse
from allyakkkuk.auth.cookies import set_no_store_headers
from allyakkkuk.auth.current_user_dependencies import require_current_user
from allyakkkuk.auth.current_user_service import AuthenticatedUser
from allyakkkuk.db.session import get_db_session
from allyakkkuk.notification.repository import SQLAlchemyNotificationRepository
from allyakkkuk.notification.schemas import (
    NotificationListItemResponse,
    NotificationListResponse,
    NotificationReadResponse,
    NotificationType,
)
from allyakkkuk.notification.service import NotificationService
from allyakkkuk.ports.clock import SystemClock

router = APIRouter(prefix="/notifications", tags=["알림"])
_clock = SystemClock()


def get_notification_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> NotificationService:
    return NotificationService(SQLAlchemyNotificationRepository(session), _clock)


def _error_response(
    description: str,
    code: str,
    message: str,
) -> dict[str, Any]:
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": code,
                        "message": message,
                        "fields": [],
                        "request_id": "opaque-request-id",
                    }
                }
            }
        },
    }


_PRIVATE_RESPONSE_HEADERS = {
    "Cache-Control": {
        "description": "개인 알림 응답 캐시 금지",
        "schema": {"type": "string", "example": "no-store"},
    }
}


@router.get(
    "",
    response_model=NotificationListResponse,
    responses={
        200: {
            "description": "현재 사용자의 화면 알림 페이지",
            "headers": _PRIVATE_RESPONSE_HEADERS,
        },
        401: _error_response("access 인증 실패", "AUTH_REQUIRED", "인증이 필요합니다."),
        503: _error_response(
            "PostgreSQL 조회 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="내 화면 알림 목록 조회",
    operation_id="notification_list",
)
def list_notifications(
    response: Response,
    current: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> NotificationListResponse:
    result = service.list_notifications(
        user_id=current.user_id,
        page=page,
        page_size=page_size,
    )
    set_no_store_headers(response)
    return NotificationListResponse(
        items=[
            NotificationListItemResponse(
                id=item.id,
                care_item_id=item.care_item_id,
                product_name=item.product_name,
                notification_type=cast(NotificationType, item.notification_type),
                reference_date=item.reference_date,
                trigger_days_before=cast(Any, item.trigger_days_before),
                scheduled_at=item.scheduled_at,
                created_at=item.created_at,
                read_at=item.read_at,
                is_read=item.is_read,
            )
            for item in result.items
        ],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        has_next=result.has_next,
    )


@router.put(
    "/{notification_id}/read",
    response_model=NotificationReadResponse,
    responses={
        200: {
            "description": "현재 사용자의 알림 읽음 처리",
            "headers": _PRIVATE_RESPONSE_HEADERS,
        },
        401: _error_response("access 인증 실패", "AUTH_REQUIRED", "인증이 필요합니다."),
        404: _error_response(
            "현재 사용자의 알림 없음",
            "NOTIFICATION_NOT_FOUND",
            "알림을 찾을 수 없습니다.",
        ),
        503: _error_response(
            "PostgreSQL 갱신 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="내 화면 알림 읽음 처리",
    operation_id="notification_mark_read",
)
def mark_notification_read(
    notification_id: UUID,
    response: Response,
    current: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationReadResponse:
    result = service.mark_read(
        user_id=current.user_id,
        notification_id=notification_id,
    )
    set_no_store_headers(response)
    return NotificationReadResponse(id=result.id, read_at=result.read_at)
