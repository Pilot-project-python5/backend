from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import cast
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import Session

import yeongyangkkuk.notification.job as job_module
from yeongyangkkuk.adapters.email import FakeEmailSender
from yeongyangkkuk.notification.email_service import EmailReminderSummary
from yeongyangkkuk.notification.job import NotificationJob
from yeongyangkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.12")]


class StubSessionContext:
    def __init__(self) -> None:
        self.entered = False
        self.exited = False

    def __enter__(self) -> Session:
        self.entered = True
        return cast(Session, self)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.exited = True


def test_notification_job_runs_email_after_both_logical_event_generators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_context = StubSessionContext()
    sender = FakeEmailSender()
    runs: list[str] = []

    def session_factory() -> Session:
        return cast(Session, session_context)

    monkeypatch.setattr(
        job_module,
        "SQLAlchemyRepurchaseNotificationRepository",
        lambda session: object(),
    )
    monkeypatch.setattr(
        job_module,
        "SQLAlchemyExpirationNotificationRepository",
        lambda session: object(),
    )
    monkeypatch.setattr(
        job_module, "SQLAlchemyEmailDeliveryRepository", lambda session: object()
    )

    class StubRepurchaseService:
        def __init__(self, repository: object, clock: object, zone: ZoneInfo) -> None:
            pass

        def run(self) -> int:
            runs.append("REPURCHASE")
            return 1

    class StubExpirationService:
        def __init__(self, repository: object, clock: object, zone: ZoneInfo) -> None:
            pass

        def run(self) -> int:
            runs.append("EXPIRATION")
            return 1

    class StubEmailService:
        def __init__(
            self,
            repository: object,
            sender_arg: object,
            clock: object,
            zone: ZoneInfo,
        ) -> None:
            assert sender_arg is sender

        def run(self) -> EmailReminderSummary:
            runs.append("EMAIL")
            return EmailReminderSummary(2, 2, 0, 0)

    monkeypatch.setattr(
        job_module, "RepurchaseNotificationService", StubRepurchaseService
    )
    monkeypatch.setattr(
        job_module, "ExpirationNotificationService", StubExpirationService
    )
    monkeypatch.setattr(job_module, "EmailReminderService", StubEmailService)

    NotificationJob(
        session_factory,
        FakeClock(datetime(2026, 8, 14, 0, 0, tzinfo=UTC)),
        ZoneInfo("Asia/Seoul"),
        sender,
    ).run()

    assert session_context.entered is True
    assert session_context.exited is True
    assert runs == ["REPURCHASE", "EXPIRATION", "EMAIL"]
