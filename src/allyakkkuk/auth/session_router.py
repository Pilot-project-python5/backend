"""refresh token 회전과 현재 세션 로그아웃 API."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from allyakkkuk.api.error_handlers import app_error_response
from allyakkkuk.api.schemas import ErrorResponse
from allyakkkuk.auth.cookies import (
    REFRESH_COOKIE_NAME,
    SessionCookiePolicy,
    clear_auth_cookies,
    set_auth_cookies,
    set_no_store_headers,
)
from allyakkkuk.auth.session_repository import SQLAlchemySessionRepository
from allyakkkuk.auth.session_schemas import SessionRefreshResponse
from allyakkkuk.auth.session_service import SessionService
from allyakkkuk.auth.tokens import JwtSessionTokenIssuer
from allyakkkuk.core.config import get_settings
from allyakkkuk.core.errors import AppError
from allyakkkuk.db.session import get_db_session
from allyakkkuk.ports.clock import SystemClock

router = APIRouter(prefix="/auth", tags=["인증"])
_settings = get_settings()
_clock = SystemClock()
_token_rotator = JwtSessionTokenIssuer(_settings.auth_token_secret.get_secret_value())


def get_session_cookie_policy() -> SessionCookiePolicy:
    return SessionCookiePolicy(secure=_settings.auth_cookie_secure)


def get_session_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> SessionService:
    return SessionService(
        repository=SQLAlchemySessionRepository(session),
        token_rotator=_token_rotator,
        clock=_clock,
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


_SUCCESS_HEADERS = {
    "Set-Cookie": {
        "description": "회전 또는 삭제되는 access·refresh HttpOnly 쿠키",
        "schema": {"type": "string"},
    },
    "Cache-Control": {
        "description": "인증 응답 캐시 금지",
        "schema": {"type": "string", "example": "no-store"},
    },
}


@router.post(
    "/refresh",
    response_model=SessionRefreshResponse,
    responses={
        200: {
            "description": "현재 refresh 세션 회전 성공",
            "headers": _SUCCESS_HEADERS,
        },
        401: {
            **_error_response(
                "refresh 세션 무효",
                "AUTH_SESSION_INVALID",
                "유효하지 않은 인증 세션입니다.",
            ),
            "headers": _SUCCESS_HEADERS,
        },
        503: _error_response(
            "PostgreSQL 처리 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="인증 세션 갱신",
    operation_id="auth_refresh_session",
)
def refresh_session(
    request: Request,
    response: Response,
    service: Annotated[SessionService, Depends(get_session_service)],
    cookie_policy: Annotated[
        SessionCookiePolicy,
        Depends(get_session_cookie_policy),
    ],
    refresh_token: Annotated[
        str | None,
        Cookie(alias=REFRESH_COOKIE_NAME),
    ] = None,
) -> SessionRefreshResponse | JSONResponse:
    try:
        result = service.refresh(refresh_token)
    except AppError as exc:
        if exc.code != "AUTH_SESSION_INVALID":
            raise
        error_response = app_error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
        )
        set_no_store_headers(error_response)
        clear_auth_cookies(error_response, cookie_policy)
        return error_response

    set_no_store_headers(response)
    set_auth_cookies(
        response,
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        authenticated_at=result.authenticated_at,
        access_token_expires_at=result.access_token_expires_at,
        refresh_token_expires_at=result.refresh_token_expires_at,
        policy=cookie_policy,
    )
    return SessionRefreshResponse(
        authenticated_at=result.authenticated_at,
        access_token_expires_at=result.access_token_expires_at,
        refresh_token_expires_at=result.refresh_token_expires_at,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        204: {
            "description": "현재 세션 폐기 또는 이미 로그아웃 상태",
            "headers": _SUCCESS_HEADERS,
        },
        503: _error_response(
            "PostgreSQL 처리 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="현재 기기 로그아웃",
    operation_id="auth_logout",
)
def logout(
    response: Response,
    service: Annotated[SessionService, Depends(get_session_service)],
    cookie_policy: Annotated[
        SessionCookiePolicy,
        Depends(get_session_cookie_policy),
    ],
    refresh_token: Annotated[
        str | None,
        Cookie(alias=REFRESH_COOKIE_NAME),
    ] = None,
) -> Response:
    service.logout(refresh_token)
    response.status_code = status.HTTP_204_NO_CONTENT
    set_no_store_headers(response)
    clear_auth_cookies(response, cookie_policy)
    return response
