from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import cast
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import Session

import yeongyangkkuk.notification.job as job_module
from yeongyangkkuk.notification.job import RepurchaseNotificationJob
from yeongyangkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.8")]


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


def test_worker_job_opens_one_session_and_runs_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_context = StubSessionContext()
    repository = object()
    calls: list[tuple[object, object, ZoneInfo]] = []

    def session_factory() -> Session:
        return cast(Session, session_context)

    class StubService:
        def __init__(
            self,
            repository_arg: object,
            clock_arg: object,
            time_zone_arg: ZoneInfo,
        ) -> None:
            calls.append((repository_arg, clock_arg, time_zone_arg))

        def run(self) -> int:
            return 2

    monkeypatch.setattr(
        job_module,
        "SQLAlchemyRepurchaseNotificationRepository",
        lambda session: repository,
    )
    monkeypatch.setattr(job_module, "RepurchaseNotificationService", StubService)
    clock = FakeClock(datetime(2026, 8, 14, 0, 0, tzinfo=UTC))
    time_zone = ZoneInfo("Asia/Seoul")

    RepurchaseNotificationJob(session_factory, clock, time_zone).run()

    assert session_context.entered is True
    assert session_context.exited is True
    assert calls == [(repository, clock, time_zone)]
