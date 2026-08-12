"""복용 제품 등록 API."""

from __future__ import annotations

from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from allyakkkuk.api.schemas import ErrorResponse
from allyakkkuk.auth.cookies import set_no_store_headers
from allyakkkuk.auth.current_user_dependencies import require_current_user
from allyakkkuk.auth.current_user_service import AuthenticatedUser
from allyakkkuk.care.care_item_repository import SQLAlchemyCareItemRepository
from allyakkkuk.care.care_item_schemas import CareItemCreateRequest, CareItemResponse
from allyakkkuk.care.care_item_service import (
    CareItemRegistrationCommand,
    CareItemService,
)
from allyakkkuk.core.config import get_settings
from allyakkkuk.db.session import get_db_session
from allyakkkuk.ports.clock import SystemClock

router = APIRouter(prefix="/care", tags=["마이케어"])
_clock = SystemClock()
_settings = get_settings()
_time_zone = ZoneInfo(_settings.app_timezone)


def get_care_item_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> CareItemService:
    return CareItemService(
        SQLAlchemyCareItemRepository(session),
        _clock,
        _time_zone,
    )


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


@router.post(
    "/items",
    response_model=CareItemResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "복용 제품 등록 성공",
            "headers": {
                "Cache-Control": {
                    "description": "개인 건강 관련 응답 캐시 금지",
                    "schema": {"type": "string", "example": "no-store"},
                }
            },
        },
        401: _error_response(
            "access 인증 실패",
            "AUTH_REQUIRED",
            "인증이 필요합니다.",
        ),
        404: _error_response(
            "카탈로그 제품 없음",
            "PRODUCT_NOT_FOUND",
            "제품을 찾을 수 없습니다.",
        ),
        422: _error_response(
            "등록 값 검증 실패",
            "VALIDATION_FAILED",
            "요청 값을 확인해주세요.",
        ),
        503: _error_response(
            "PostgreSQL 처리 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="복용 제품 등록",
    operation_id="care_register_item",
)
def register_care_item(
    payload: CareItemCreateRequest,
    response: Response,
    current: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[CareItemService, Depends(get_care_item_service)],
) -> CareItemResponse:
    result = service.register(
        user_id=current.user_id,
        command=CareItemRegistrationCommand(
            product_id=payload.product_id,
            purchase_date=payload.purchase_date,
            intake_start_date=payload.intake_start_date,
            total_quantity=payload.total_quantity,
            dose_per_intake=payload.dose_per_intake,
            intakes_per_day=payload.intakes_per_day,
        ),
    )
    set_no_store_headers(response)
    return CareItemResponse(
        id=result.id,
        product_id=result.product_id,
        purchase_date=result.purchase_date,
        intake_start_date=result.intake_start_date,
        total_quantity=result.total_quantity,
        dose_per_intake=result.dose_per_intake,
        intakes_per_day=result.intakes_per_day,
        created_at=result.created_at,
    )
