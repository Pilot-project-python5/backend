from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import cast
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import Session

import allyakkkuk.notification.job as job_module
from allyakkkuk.notification.job import NotificationJob
from allyakkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.9")]


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


def test_notification_job_runs_both_logical_event_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_context = StubSessionContext()
    repurchase_repository = object()
    expiration_repository = object()
    runs: list[str] = []

    def session_factory() -> Session:
        return cast(Session, session_context)

    class StubRepurchaseService:
        def __init__(self, repository: object, clock: object, zone: ZoneInfo) -> None:
            assert repository is repurchase_repository

        def run(self) -> int:
            runs.append("REPURCHASE")
            return 2

    class StubExpirationService:
        def __init__(self, repository: object, clock: object, zone: ZoneInfo) -> None:
            assert repository is expiration_repository

        def run(self) -> int:
            runs.append("EXPIRATION")
            return 3

    monkeypatch.setattr(
        job_module,
        "SQLAlchemyRepurchaseNotificationRepository",
        lambda session: repurchase_repository,
    )
    monkeypatch.setattr(
        job_module,
        "SQLAlchemyExpirationNotificationRepository",
        lambda session: expiration_repository,
    )
    monkeypatch.setattr(
        job_module, "RepurchaseNotificationService", StubRepurchaseService
    )
    monkeypatch.setattr(
        job_module, "ExpirationNotificationService", StubExpirationService
    )

    NotificationJob(
        session_factory,
        FakeClock(datetime(2026, 8, 14, 0, 0, tzinfo=UTC)),
        ZoneInfo("Asia/Seoul"),
    ).run()

    assert session_context.entered is True
    assert session_context.exited is True
    assert runs == ["REPURCHASE", "EXPIRATION"]
