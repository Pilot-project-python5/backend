"""현재 로그인 사용자와 세션 상태 조회 API."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response

from allyakkkuk.api.schemas import ErrorResponse
from allyakkkuk.auth.cookies import set_no_store_headers
from allyakkkuk.auth.current_user_dependencies import require_current_user
from allyakkkuk.auth.current_user_schemas import (
    CurrentSessionView,
    CurrentUserResponse,
    CurrentUserView,
)
from allyakkkuk.auth.current_user_service import AuthenticatedUser

router = APIRouter(prefix="/auth", tags=["인증"])


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


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    responses={
        200: {
            "description": "현재 사용자와 access·refresh 세션 만료 상태",
            "headers": {
                "Cache-Control": {
                    "description": "개인 인증 응답 캐시 금지",
                    "schema": {"type": "string", "example": "no-store"},
                }
            },
        },
        401: _error_response(
            "access 인증 실패",
            "AUTH_REQUIRED",
            "인증이 필요합니다.",
        ),
        503: _error_response(
            "PostgreSQL 조회 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="현재 사용자와 세션 상태 확인",
    operation_id="auth_get_current_user",
)
def get_current_user(
    response: Response,
    current: Annotated[AuthenticatedUser, Depends(require_current_user)],
) -> CurrentUserResponse:
    set_no_store_headers(response)
    return CurrentUserResponse(
        user=CurrentUserView(
            id=current.user_id,
            login_id=current.login_id,
            name=current.name,
            email=current.email,
            status=current.status,
            email_verified_at=current.email_verified_at,
            birth_date=current.birth_date,
            gender=current.gender,
            height_cm=current.height_cm,
            weight_kg=current.weight_kg,
        ),
        session=CurrentSessionView(
            access_token_expires_at=current.access_token_expires_at,
            refresh_token_expires_at=current.refresh_token_expires_at,
        ),
    )
