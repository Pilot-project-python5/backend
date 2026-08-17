"""아이디·비밀번호 로그인 API와 세션 쿠키 정책."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from yeongyangkkuk.api.schemas import ErrorResponse
from yeongyangkkuk.auth.cookies import (
    SessionCookiePolicy,
    set_auth_cookies,
    set_no_store_headers,
)
from yeongyangkkuk.auth.login_repository import SQLAlchemyLoginRepository
from yeongyangkkuk.auth.login_schemas import (
    LoginRequest,
    LoginResponse,
    reveal_password,
)
from yeongyangkkuk.auth.login_service import LoginCommand, LoginService
from yeongyangkkuk.auth.passwords import Argon2PasswordHasher
from yeongyangkkuk.auth.tokens import JwtSessionTokenIssuer
from yeongyangkkuk.core.config import get_settings
from yeongyangkkuk.db.session import get_db_session
from yeongyangkkuk.ports.clock import SystemClock

router = APIRouter(prefix="/auth", tags=["인증"])
_settings = get_settings()
_password_hasher = Argon2PasswordHasher()
_dummy_password_hash = _password_hasher.hash("Dummy!Pass123")
_token_issuer = JwtSessionTokenIssuer(_settings.auth_token_secret.get_secret_value())
_clock = SystemClock()


LoginCookiePolicy = SessionCookiePolicy


def get_login_cookie_policy() -> LoginCookiePolicy:
    return SessionCookiePolicy(secure=_settings.auth_cookie_secure)


def get_login_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> LoginService:
    return LoginService(
        repository=SQLAlchemyLoginRepository(session),
        password_hasher=_password_hasher,
        dummy_password_hash=_dummy_password_hash,
        token_issuer=_token_issuer,
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


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        200: {
            "description": "로그인 성공. access·refresh token은 HttpOnly 쿠키로 전달",
            "headers": {
                "Set-Cookie": {
                    "description": "access token과 refresh token HttpOnly 쿠키",
                    "schema": {"type": "string"},
                },
                "Cache-Control": {
                    "description": "인증 응답 캐시 금지",
                    "schema": {"type": "string", "example": "no-store"},
                },
            },
        },
        401: _error_response(
            "아이디 또는 비밀번호 불일치",
            "AUTH_INVALID_CREDENTIALS",
            "아이디 또는 비밀번호가 올바르지 않습니다.",
        ),
        403: {
            "model": ErrorResponse,
            "description": "이메일 미인증 또는 정지 계정",
            "content": {
                "application/json": {
                    "examples": {
                        "email_unverified": {
                            "summary": "AUTH_EMAIL_UNVERIFIED",
                            "value": {
                                "error": {
                                    "code": "AUTH_EMAIL_UNVERIFIED",
                                    "message": "이메일 인증이 필요합니다.",
                                    "fields": [],
                                    "request_id": "opaque-request-id",
                                }
                            },
                        },
                        "account_suspended": {
                            "summary": "AUTH_ACCOUNT_SUSPENDED",
                            "value": {
                                "error": {
                                    "code": "AUTH_ACCOUNT_SUSPENDED",
                                    "message": "정지된 계정입니다.",
                                    "fields": [],
                                    "request_id": "opaque-request-id",
                                }
                            },
                        },
                    }
                }
            },
        },
        422: _error_response(
            "요청 형식 검증 실패",
            "VALIDATION_FAILED",
            "요청 값을 확인해주세요.",
        ),
        503: _error_response(
            "PostgreSQL 처리 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="로그인",
    operation_id="auth_login",
)
def login(
    payload: LoginRequest,
    response: Response,
    service: Annotated[LoginService, Depends(get_login_service)],
    cookie_policy: Annotated[
        LoginCookiePolicy,
        Depends(get_login_cookie_policy),
    ],
) -> LoginResponse:
    result = service.login(
        LoginCommand(
            login_id=payload.login_id,
            password=reveal_password(payload.password),
        )
    )
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
    return LoginResponse(
        user_id=result.user_id,
        login_id=result.login_id,
        name=result.name,
        status=result.status,
        authenticated_at=result.authenticated_at,
        access_token_expires_at=result.access_token_expires_at,
        refresh_token_expires_at=result.refresh_token_expires_at,
    )
