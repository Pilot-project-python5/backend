"""회원가입과 로그인 아이디 조회 API 라우터."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from allyakkkuk.api.schemas import ErrorResponse
from allyakkkuk.auth.passwords import Argon2PasswordHasher
from allyakkkuk.auth.repository import (
    SQLAlchemyLoginIdAvailabilityRepository,
    SQLAlchemySignupRepository,
)
from allyakkkuk.auth.schemas import (
    LoginIdAvailabilityQuery,
    LoginIdAvailabilityResponse,
    SignupRequest,
    SignupResponse,
)
from allyakkkuk.auth.service import (
    LoginIdAvailabilityService,
    SignupCommand,
    SignupService,
)
from allyakkkuk.db.session import get_db_session
from allyakkkuk.ports.clock import SystemClock

router = APIRouter(prefix="/auth", tags=["인증"])
_password_hasher = Argon2PasswordHasher()
_clock = SystemClock()


def get_signup_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> SignupService:
    return SignupService(
        repository=SQLAlchemySignupRepository(session),
        password_hasher=_password_hasher,
        clock=_clock,
    )


def get_login_id_availability_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> LoginIdAvailabilityService:
    return LoginIdAvailabilityService(
        repository=SQLAlchemyLoginIdAvailabilityRepository(session)
    )


def _error_example(code: str, message: str) -> dict[str, Any]:
    return {
        "summary": code,
        "value": {
            "error": {
                "code": code,
                "message": message,
                "fields": [],
                "request_id": "opaque-request-id",
            }
        },
    }


@router.get(
    "/login-id/availability",
    response_model=LoginIdAvailabilityResponse,
    responses={
        422: {
            "model": ErrorResponse,
            "description": "로그인 아이디 형식 검증 실패",
            "content": {
                "application/json": {
                    "example": _error_example(
                        "VALIDATION_FAILED", "요청 값을 확인해주세요."
                    )["value"]
                }
            },
        },
        503: {
            "model": ErrorResponse,
            "description": "PostgreSQL 조회 실패",
            "content": {
                "application/json": {
                    "example": _error_example(
                        "SERVICE_UNAVAILABLE", "서비스가 아직 준비되지 않았습니다."
                    )["value"]
                }
            },
        },
    },
    summary="로그인 아이디 사용 가능 여부 확인",
    operation_id="auth_check_login_id_availability",
)
def check_login_id_availability(
    query: Annotated[LoginIdAvailabilityQuery, Depends()],
    service: Annotated[
        LoginIdAvailabilityService,
        Depends(get_login_id_availability_service),
    ],
) -> LoginIdAvailabilityResponse:
    result = service.check(query.login_id)
    return LoginIdAvailabilityResponse(
        login_id=result.login_id,
        available=result.available,
    )


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {
            "model": ErrorResponse,
            "description": "로그인 아이디 또는 이메일 중복",
            "content": {
                "application/json": {
                    "examples": {
                        "login_id": _error_example(
                            "AUTH_LOGIN_ID_UNAVAILABLE", "사용할 수 없는 아이디입니다."
                        ),
                        "email": _error_example(
                            "AUTH_EMAIL_UNAVAILABLE", "사용할 수 없는 이메일입니다."
                        ),
                    }
                }
            },
        },
        422: {
            "model": ErrorResponse,
            "description": "가입 정보 검증 실패",
            "content": {
                "application/json": {
                    "example": _error_example(
                        "VALIDATION_FAILED", "요청 값을 확인해주세요."
                    )["value"]
                }
            },
        },
        503: {
            "model": ErrorResponse,
            "description": "PostgreSQL 처리 실패",
            "content": {
                "application/json": {
                    "example": _error_example(
                        "SERVICE_UNAVAILABLE", "서비스가 아직 준비되지 않았습니다."
                    )["value"]
                }
            },
        },
    },
    summary="이메일 미인증 회원가입",
    operation_id="auth_signup",
)
def signup(
    payload: SignupRequest,
    service: Annotated[SignupService, Depends(get_signup_service)],
) -> SignupResponse:
    result = service.signup(
        SignupCommand(
            name=payload.name,
            login_id=payload.login_id,
            password=payload.password.get_secret_value(),
            email=str(payload.email),
            birth_date=payload.birth_date,
            gender=payload.gender,
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
        )
    )
    return SignupResponse(
        id=result.id,
        login_id=result.login_id,
        email=result.email,
        status=result.status,
        created_at=result.created_at,
    )
