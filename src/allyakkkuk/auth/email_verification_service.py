"""이메일 인증번호 발급·재전송·확인 애플리케이션 서비스."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from allyakkkuk.auth.email_verification import (
    VerificationCodeGenerator,
    VerificationCodeHasher,
)
from allyakkkuk.auth.email_verification_repository import (
    EmailVerificationCreateData,
    EmailVerificationPersistenceError,
    EmailVerificationRepository,
)
from allyakkkuk.auth.models import EmailVerificationPurpose, UserStatus
from allyakkkuk.core.errors import AppError
from allyakkkuk.ports.clock import Clock
from allyakkkuk.ports.email import EmailDeliveryError, EmailSender, OutboundEmail

CODE_VALIDITY = timedelta(minutes=10)
RESEND_DELAY = timedelta(seconds=60)
MAX_FAILED_ATTEMPTS = 5


@dataclass(frozen=True, slots=True)
class EmailVerificationIssueResult:
    verification_id: UUID
    expires_at: datetime
    resend_available_at: datetime


@dataclass(frozen=True, slots=True)
class EmailVerificationSuccessResult:
    user_id: UUID
    status: UserStatus
    email_verified_at: datetime


class EmailVerificationService:
    def __init__(
        self,
        *,
        repository: EmailVerificationRepository,
        code_generator: VerificationCodeGenerator,
        code_hasher: VerificationCodeHasher,
        email_sender: EmailSender,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._code_generator = code_generator
        self._code_hasher = code_hasher
        self._email_sender = email_sender
        self._clock = clock

    def issue(self, user_id: UUID) -> EmailVerificationIssueResult:
        return self._issue(user_id)

    def resend(self, user_id: UUID) -> EmailVerificationIssueResult:
        return self._issue(user_id)

    def _issue(self, user_id: UUID) -> EmailVerificationIssueResult:
        now = self._clock.now()
        try:
            user = self._repository.get_user_for_update(user_id)
            if user is None:
                raise _not_found()
            if user.status == UserStatus.ACTIVE or user.email_verified_at is not None:
                raise AppError(
                    status_code=409,
                    code="AUTH_EMAIL_ALREADY_VERIFIED",
                    message="이미 이메일 인증이 완료되었습니다.",
                )
            if user.status != UserStatus.PENDING_EMAIL_VERIFICATION:
                raise AppError(
                    status_code=409,
                    code="AUTH_VERIFICATION_NOT_ACTIVE",
                    message="이메일 인증을 진행할 수 없는 계정 상태입니다.",
                )

            latest = self._repository.get_latest_for_update(user_id)
            if latest is not None and now < latest.resend_available_at:
                raise AppError(
                    status_code=429,
                    code="AUTH_VERIFICATION_RESEND_TOO_SOON",
                    message="잠시 후 인증번호를 다시 요청해주세요.",
                )

            verification_id = uuid4()
            code = self._code_generator.generate()
            code_hash = self._code_hasher.hash(verification_id, code)
            if (
                latest is not None
                and latest.used_at is None
                and latest.superseded_at is None
            ):
                self._repository.supersede(latest.id, now)

            data = EmailVerificationCreateData(
                id=verification_id,
                user_id=user_id,
                purpose=EmailVerificationPurpose.VERIFY_EMAIL.value,
                code_hash=code_hash,
                expires_at=now + CODE_VALIDITY,
                resend_available_at=now + RESEND_DELAY,
                created_at=now,
            )
            self._repository.add(data)
            self._email_sender.send(_verification_email(user.email, code))
            self._repository.commit()
        except EmailDeliveryError as exc:
            self._repository.rollback()
            raise _service_unavailable() from exc
        except EmailVerificationPersistenceError as exc:
            self._repository.rollback()
            raise _service_unavailable() from exc

        return EmailVerificationIssueResult(
            verification_id=verification_id,
            expires_at=data.expires_at,
            resend_available_at=data.resend_available_at,
        )

    def confirm(
        self, verification_id: UUID, code: str
    ) -> EmailVerificationSuccessResult:
        now = self._clock.now()
        try:
            user_id = self._repository.find_user_id(verification_id)
            if user_id is None:
                raise _not_found()

            user = self._repository.get_user_for_update(user_id)
            verification = self._repository.get_for_update(verification_id)
            if user is None or verification is None:
                raise _not_found()
            if verification.user_id != user.id:
                raise _not_found()
            if (
                verification.used_at is not None
                or verification.superseded_at is not None
            ):
                raise AppError(
                    status_code=409,
                    code="AUTH_VERIFICATION_NOT_ACTIVE",
                    message="사용할 수 없는 인증번호입니다.",
                )
            if user.status == UserStatus.ACTIVE or user.email_verified_at is not None:
                raise AppError(
                    status_code=409,
                    code="AUTH_EMAIL_ALREADY_VERIFIED",
                    message="이미 이메일 인증이 완료되었습니다.",
                )
            if verification.failed_attempts >= MAX_FAILED_ATTEMPTS:
                raise _too_many_attempts()
            if now >= verification.expires_at:
                raise AppError(
                    status_code=410,
                    code="AUTH_VERIFICATION_EXPIRED",
                    message="인증번호가 만료되었습니다.",
                )

            if not self._code_hasher.verify(
                verification_id, code, verification.code_hash
            ):
                attempts = min(
                    verification.failed_attempts + 1,
                    MAX_FAILED_ATTEMPTS,
                )
                self._repository.set_failed_attempts(verification_id, attempts)
                self._repository.commit()
                if attempts >= MAX_FAILED_ATTEMPTS:
                    raise _too_many_attempts()
                raise AppError(
                    status_code=400,
                    code="AUTH_VERIFICATION_CODE_INVALID",
                    message="인증번호가 올바르지 않습니다.",
                )

            self._repository.complete(verification_id, user_id, now)
            self._repository.commit()
        except EmailVerificationPersistenceError as exc:
            self._repository.rollback()
            raise _service_unavailable() from exc

        return EmailVerificationSuccessResult(
            user_id=user_id,
            status=UserStatus.ACTIVE,
            email_verified_at=now,
        )


def _verification_email(recipient: str, code: str) -> OutboundEmail:
    return OutboundEmail(
        recipients=(recipient,),
        subject="알약꾹 이메일 인증번호",
        text_body=(
            "알약꾹 이메일 인증번호는 "
            f"{code} 입니다. 인증번호는 10분 동안 사용할 수 있습니다."
        ),
        html_body=(
            "<p>알약꾹 이메일 인증번호는 "
            f"<strong>{code}</strong> 입니다.</p>"
            "<p>인증번호는 10분 동안 사용할 수 있습니다.</p>"
        ),
    )


def _not_found() -> AppError:
    return AppError(
        status_code=404,
        code="RESOURCE_NOT_FOUND",
        message="요청한 리소스를 찾을 수 없습니다.",
    )


def _too_many_attempts() -> AppError:
    return AppError(
        status_code=429,
        code="AUTH_VERIFICATION_TOO_MANY_ATTEMPTS",
        message="인증번호 확인 횟수를 초과했습니다. 새 인증번호를 요청해주세요.",
    )


def _service_unavailable() -> AppError:
    return AppError(
        status_code=503,
        code="SERVICE_UNAVAILABLE",
        message="서비스가 아직 준비되지 않았습니다.",
    )
