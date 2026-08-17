from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from yeongyangkkuk.notification.email_repository import (
    EmailDeliveryClaim,
    EmailDeliveryRepository,
    EmailDeliveryStatus,
)
from yeongyangkkuk.notification.email_service import (
    EmailReminderError,
    EmailReminderService,
)
from yeongyangkkuk.notification.repository import NotificationPersistenceError
from yeongyangkkuk.ports.clock import FakeClock
from yeongyangkkuk.ports.email import EmailDeliveryError, EmailSender, OutboundEmail

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.12")]

NOW = datetime(2026, 8, 14, 0, 0, tzinfo=UTC)
DELIVERY_ID = UUID("51000000-0000-4000-8000-000000000412")
NOTIFICATION_ID = UUID("41000000-0000-4000-8000-000000000412")


def claim(*, attempt_count: int = 1, kind: str = "REPURCHASE") -> EmailDeliveryClaim:
    return EmailDeliveryClaim(
        id=DELIVERY_ID,
        notification_id=NOTIFICATION_ID,
        recipient_email="reminder-412@example.com",
        notification_type=kind,
        product_name="리마인더 테스트 제품",
        reference_date=date(2026, 8, 19),
        trigger_days_before=5,
        attempt_count=attempt_count,
    )


class StubRepository(EmailDeliveryRepository):
    def __init__(self, claims: list[EmailDeliveryClaim] | None = None) -> None:
        self.claims = list(claims or [])
        self.fails = False
        self.enqueue_calls: list[tuple[datetime, datetime]] = []
        self.finalize_calls: list[tuple[datetime, int]] = []
        self.claim_calls: list[tuple[datetime, datetime, int]] = []
        self.sent_calls: list[tuple[UUID, int, datetime]] = []
        self.failed_calls: list[tuple[UUID, int, datetime, datetime, int, str]] = []

    def enqueue_for_schedule(
        self, *, scheduled_at: datetime, created_at: datetime
    ) -> int:
        if self.fails:
            raise NotificationPersistenceError
        self.enqueue_calls.append((scheduled_at, created_at))
        return 1

    def finalize_expired_final_attempts(
        self, *, now: datetime, max_attempts: int
    ) -> int:
        self.finalize_calls.append((now, max_attempts))
        return 0

    def claim_due(
        self,
        *,
        now: datetime,
        lease_until: datetime,
        max_attempts: int,
    ) -> EmailDeliveryClaim | None:
        self.claim_calls.append((now, lease_until, max_attempts))
        return self.claims.pop(0) if self.claims else None

    def mark_sent(
        self,
        *,
        delivery_id: UUID,
        attempt_count: int,
        sent_at: datetime,
    ) -> bool:
        self.sent_calls.append((delivery_id, attempt_count, sent_at))
        return True

    def mark_failed(
        self,
        *,
        delivery_id: UUID,
        attempt_count: int,
        failed_at: datetime,
        retry_at: datetime,
        max_attempts: int,
        error_code: str,
    ) -> EmailDeliveryStatus | None:
        self.failed_calls.append(
            (
                delivery_id,
                attempt_count,
                failed_at,
                retry_at,
                max_attempts,
                error_code,
            )
        )
        return "RETRY" if attempt_count < max_attempts else "FAILED"


class RecordingSender(EmailSender):
    def __init__(self, *, fails: bool = False) -> None:
        self.fails = fails
        self.messages: list[OutboundEmail] = []

    def send(self, message: OutboundEmail) -> None:
        self.messages.append(message)
        if self.fails:
            raise EmailDeliveryError


def service(
    repository: StubRepository,
    sender: RecordingSender,
    *,
    now: datetime = NOW,
) -> EmailReminderService:
    return EmailReminderService(
        repository,
        sender,
        FakeClock(now),
        ZoneInfo("Asia/Seoul"),
    )


def test_after_nine_enqueues_today_schedule_and_sends_due_delivery() -> None:
    repository = StubRepository([claim()])
    sender = RecordingSender()

    result = service(repository, sender).run()

    assert repository.enqueue_calls == [(NOW, NOW)]
    assert repository.finalize_calls == [(NOW, 3)]
    assert repository.claim_calls[0] == (NOW, NOW + timedelta(minutes=5), 3)
    assert repository.sent_calls == [(DELIVERY_ID, 1, NOW)]
    assert result.enqueued == result.sent == 1
    assert result.retry_scheduled == result.failed == 0
    assert sender.messages[0].recipients == ("reminder-412@example.com",)


def test_before_nine_skips_new_enqueue_but_processes_due_retry() -> None:
    before_nine = datetime(2026, 8, 13, 23, 59, tzinfo=UTC)
    repository = StubRepository([claim(attempt_count=2, kind="EXPIRATION")])
    sender = RecordingSender()

    result = service(repository, sender, now=before_nine).run()

    assert repository.enqueue_calls == []
    assert result.sent == 1
    assert "유통기한" in sender.messages[0].subject


def test_smtp_failures_schedule_retry_then_final_failure_and_continue() -> None:
    repository = StubRepository([claim(attempt_count=2), claim(attempt_count=3)])
    sender = RecordingSender(fails=True)

    result = service(repository, sender).run()

    assert len(sender.messages) == 2
    assert [call[1] for call in repository.failed_calls] == [2, 3]
    assert all(
        call[3] == NOW + timedelta(minutes=5) for call in repository.failed_calls
    )
    assert all(call[5] == "SMTP_DELIVERY_FAILED" for call in repository.failed_calls)
    assert result.retry_scheduled == 1
    assert result.failed == 1


def test_repository_failure_is_propagated_as_worker_domain_error() -> None:
    repository = StubRepository()
    repository.fails = True

    with pytest.raises(EmailReminderError):
        service(repository, RecordingSender()).run()
