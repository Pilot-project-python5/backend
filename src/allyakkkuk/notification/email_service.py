"""논리 알림의 로컬 이메일 전달과 제한된 재시도."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from allyakkkuk.notification.email_repository import (
    EmailDeliveryClaim,
    EmailDeliveryRepository,
)
from allyakkkuk.notification.repository import NotificationPersistenceError
from allyakkkuk.ports.clock import Clock
from allyakkkuk.ports.email import (
    EmailDeliveryError,
    EmailSender,
    OutboundEmail,
)

MAX_ATTEMPTS = 3
RETRY_DELAY = timedelta(minutes=5)
MAX_BATCH_SIZE = 100
LOCAL_TRIGGER_TIME = time(9, 0)
SMTP_ERROR_CODE = "SMTP_DELIVERY_FAILED"


class EmailReminderError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class EmailReminderSummary:
    enqueued: int
    sent: int
    retry_scheduled: int
    failed: int


class EmailReminderService:
    def __init__(
        self,
        repository: EmailDeliveryRepository,
        sender: EmailSender,
        clock: Clock,
        time_zone: ZoneInfo,
    ) -> None:
        self._repository = repository
        self._sender = sender
        self._clock = clock
        self._time_zone = time_zone

    def run(self) -> EmailReminderSummary:
        now = self._clock.now()
        local_now = now.astimezone(self._time_zone)
        local_schedule = datetime.combine(
            local_now.date(), LOCAL_TRIGGER_TIME, tzinfo=self._time_zone
        )
        try:
            enqueued = 0
            if local_now >= local_schedule:
                enqueued = self._repository.enqueue_for_schedule(
                    scheduled_at=local_schedule.astimezone(UTC),
                    created_at=now,
                )
            failed = self._repository.finalize_expired_final_attempts(
                now=now,
                max_attempts=MAX_ATTEMPTS,
            )
        except NotificationPersistenceError as exc:
            raise EmailReminderError from exc

        sent = 0
        retry_scheduled = 0
        for _ in range(MAX_BATCH_SIZE):
            claim_time = self._clock.now()
            try:
                claim = self._repository.claim_due(
                    now=claim_time,
                    lease_until=claim_time + RETRY_DELAY,
                    max_attempts=MAX_ATTEMPTS,
                )
            except NotificationPersistenceError as exc:
                raise EmailReminderError from exc
            if claim is None:
                break

            try:
                self._sender.send(render_reminder_email(claim))
            except EmailDeliveryError as delivery_exc:
                failure_time = self._clock.now()
                try:
                    status = self._repository.mark_failed(
                        delivery_id=claim.id,
                        attempt_count=claim.attempt_count,
                        failed_at=failure_time,
                        retry_at=failure_time + RETRY_DELAY,
                        max_attempts=MAX_ATTEMPTS,
                        error_code=SMTP_ERROR_CODE,
                    )
                except NotificationPersistenceError as exc:
                    raise EmailReminderError from exc
                if status is None:
                    raise EmailReminderError(
                        "이메일 실패 상태 갱신 충돌"
                    ) from delivery_exc
                if status == "RETRY":
                    retry_scheduled += 1
                else:
                    failed += 1
                continue

            try:
                updated = self._repository.mark_sent(
                    delivery_id=claim.id,
                    attempt_count=claim.attempt_count,
                    sent_at=self._clock.now(),
                )
            except NotificationPersistenceError as exc:
                raise EmailReminderError from exc
            if not updated:
                raise EmailReminderError("이메일 성공 상태 갱신 충돌")
            sent += 1

        return EmailReminderSummary(
            enqueued=enqueued,
            sent=sent,
            retry_scheduled=retry_scheduled,
            failed=failed,
        )


def render_reminder_email(claim: EmailDeliveryClaim) -> OutboundEmail:
    product_name = " ".join(claim.product_name.split())
    if claim.notification_type == "REPURCHASE":
        subject_label = "재구매가"
        date_label = "예상 소진일"
    elif claim.notification_type == "EXPIRATION":
        subject_label = "유통기한이"
        date_label = "유통기한"
    else:
        raise EmailReminderError("지원하지 않는 알림 종류")

    subject = (
        f"[알약꾹] {product_name} {subject_label} "
        f"{claim.trigger_days_before}일 남았습니다"
    )
    text_body = (
        "안녕하세요, 알약꾹입니다.\n\n"
        f"{product_name}의 {date_label}은 {claim.reference_date.isoformat()}입니다.\n"
        f"D-{claim.trigger_days_before} 알림이니 제품 상태를 확인해주세요.\n\n"
        "이 메일은 알약꾹에 등록한 복용 제품 정보를 기준으로 발송되었습니다."
    )
    return OutboundEmail(
        recipients=(claim.recipient_email,),
        subject=subject,
        text_body=text_body,
    )
