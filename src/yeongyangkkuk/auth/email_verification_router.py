"""이메일 인증번호 발급·재전송·확인 API."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from yeongyangkkuk.adapters.email import SmtpEmailSender
from yeongyangkkuk.api.schemas import ErrorResponse
from yeongyangkkuk.auth.email_verification import (
    HmacVerificationCodeHasher,
    SecureVerificationCodeGenerator,
)
from yeongyangkkuk.auth.email_verification_repository import (
    SQLAlchemyEmailVerificationRepository,
)
from yeongyangkkuk.auth.email_verification_schemas import (
    EmailVerificationConfirmRequest,
    EmailVerificationConfirmResponse,
    EmailVerificationIssueRequest,
    EmailVerificationIssueResponse,
)
from yeongyangkkuk.auth.email_verification_service import EmailVerificationService
from yeongyangkkuk.core.config import get_settings
from yeongyangkkuk.db.session import get_db_session
from yeongyangkkuk.ports.clock import SystemClock

router = APIRouter(prefix="/auth", tags=["인증"])
_settings = get_settings()
_clock = SystemClock()
_code_generator = SecureVerificationCodeGenerator()
_code_hasher = HmacVerificationCodeHasher(
    _settings.email_verification_secret.get_secret_value()
)
_email_sender = SmtpEmailSender(
    host=_settings.mail_host,
    port=_settings.mail_port,
    from_address=_settings.mail_from_address,
    from_name=_settings.mail_from_name,
)


def get_email_verification_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> EmailVerificationService:
    return EmailVerificationService(
        repository=SQLAlchemyEmailVerificationRepository(session),
        code_generator=_code_generator,
        code_hasher=_code_hasher,
        email_sender=_email_sender,
        clock=_clock,
    )


def _example(code: str, message: str) -> dict[str, Any]:
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


def _error_response(
    description: str,
    examples: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {
            "application/json": {
                "examples": {
                    key: _example(code, message)
                    for key, (code, message) in examples.items()
                }
            }
        },
    }


_ISSUE_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: _error_response(
        "사용자를 찾을 수 없음",
        {"not_found": ("RESOURCE_NOT_FOUND", "요청한 리소스를 찾을 수 없습니다.")},
    ),
    409: _error_response(
        "이미 이메일 인증 완료",
        {
            "already_verified": (
                "AUTH_EMAIL_ALREADY_VERIFIED",
                "이미 이메일 인증이 완료되었습니다.",
            ),
            "account_not_active": (
                "AUTH_VERIFICATION_NOT_ACTIVE",
                "이메일 인증을 진행할 수 없는 계정 상태입니다.",
            ),
        },
    ),
    429: _error_response(
        "재전송 대기 시간 미경과",
        {
            "too_soon": (
                "AUTH_VERIFICATION_RESEND_TOO_SOON",
                "잠시 후 인증번호를 다시 요청해주세요.",
            )
        },
    ),
    422: _error_response(
        "요청 형식 검증 실패",
        {"validation": ("VALIDATION_FAILED", "요청 값을 확인해주세요.")},
    ),
    503: _error_response(
        "PostgreSQL 또는 SMTP 처리 실패",
        {
            "unavailable": (
                "SERVICE_UNAVAILABLE",
                "서비스가 아직 준비되지 않았습니다.",
            )
        },
    ),
}


@router.post(
    "/email-verifications",
    response_model=EmailVerificationIssueResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_ISSUE_RESPONSES,
    summary="이메일 인증번호 발급",
    operation_id="auth_issue_email_verification",
)
def issue_email_verification(
    payload: EmailVerificationIssueRequest,
    service: Annotated[
        EmailVerificationService,
        Depends(get_email_verification_service),
    ],
) -> EmailVerificationIssueResponse:
    result = service.issue(payload.user_id)
    return EmailVerificationIssueResponse(
        verification_id=result.verification_id,
        expires_at=result.expires_at,
        resend_available_at=result.resend_available_at,
    )


@router.post(
    "/email-verifications/resend",
    response_model=EmailVerificationIssueResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_ISSUE_RESPONSES,
    summary="이메일 인증번호 재전송",
    operation_id="auth_resend_email_verification",
)
def resend_email_verification(
    payload: EmailVerificationIssueRequest,
    service: Annotated[
        EmailVerificationService,
        Depends(get_email_verification_service),
    ],
) -> EmailVerificationIssueResponse:
    result = service.resend(payload.user_id)
    return EmailVerificationIssueResponse(
        verification_id=result.verification_id,
        expires_at=result.expires_at,
        resend_available_at=result.resend_available_at,
    )


@router.post(
    "/email-verifications/confirm",
    response_model=EmailVerificationConfirmResponse,
    responses={
        400: _error_response(
            "인증번호 불일치",
            {
                "invalid_code": (
                    "AUTH_VERIFICATION_CODE_INVALID",
                    "인증번호가 올바르지 않습니다.",
                )
            },
        ),
        404: _ISSUE_RESPONSES[404],
        409: _error_response(
            "이미 인증했거나 더 이상 사용할 수 없는 발급 건",
            {
                "not_active": (
                    "AUTH_VERIFICATION_NOT_ACTIVE",
                    "사용할 수 없는 인증번호입니다.",
                ),
                "already_verified": (
                    "AUTH_EMAIL_ALREADY_VERIFIED",
                    "이미 이메일 인증이 완료되었습니다.",
                ),
            },
        ),
        410: _error_response(
            "인증번호 만료",
            {
                "expired": (
                    "AUTH_VERIFICATION_EXPIRED",
                    "인증번호가 만료되었습니다.",
                )
            },
        ),
        429: _error_response(
            "인증번호 확인 횟수 초과",
            {
                "too_many_attempts": (
                    "AUTH_VERIFICATION_TOO_MANY_ATTEMPTS",
                    "인증번호 확인 횟수를 초과했습니다. 새 인증번호를 요청해주세요.",
                )
            },
        ),
        422: _ISSUE_RESPONSES[422],
        503: _ISSUE_RESPONSES[503],
    },
    summary="이메일 인증번호 확인",
    operation_id="auth_confirm_email_verification",
)
def confirm_email_verification(
    payload: EmailVerificationConfirmRequest,
    service: Annotated[
        EmailVerificationService,
        Depends(get_email_verification_service),
    ],
) -> EmailVerificationConfirmResponse:
    result = service.confirm(payload.verification_id, payload.code)
    return EmailVerificationConfirmResponse(
        user_id=result.user_id,
        status=result.status,
        email_verified_at=result.email_verified_at,
    )
