from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from allyakkkuk.notification.repository import (
    NotificationPersistenceError,
    RepurchaseNotificationRepository,
    RepurchaseTrigger,
)
from allyakkkuk.notification.service import (
    RepurchaseNotificationError,
    RepurchaseNotificationService,
)
from allyakkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.8")]

SEOUL = ZoneInfo("Asia/Seoul")


class StubRepository(RepurchaseNotificationRepository):
    def __init__(self, *, created: int = 3, fails: bool = False) -> None:
        self.created = created
        self.fails = fails
        self.calls: list[tuple[tuple[RepurchaseTrigger, ...], datetime, datetime]] = []

    def create_repurchase_notifications(
        self,
        *,
        triggers: tuple[RepurchaseTrigger, ...],
        scheduled_at: datetime,
        created_at: datetime,
    ) -> int:
        self.calls.append((triggers, scheduled_at, created_at))
        if self.fails:
            raise NotificationPersistenceError
        return self.created


def test_before_local_nine_does_not_query_repository() -> None:
    repository = StubRepository()
    service = RepurchaseNotificationService(
        repository,
        FakeClock(datetime(2026, 8, 13, 23, 59, 59, tzinfo=UTC)),
        SEOUL,
    )

    assert service.run() == 0
    assert repository.calls == []


def test_at_local_nine_creates_exact_trigger_dates() -> None:
    now = datetime(2026, 8, 14, 0, 0, tzinfo=UTC)
    repository = StubRepository(created=2)
    service = RepurchaseNotificationService(
        repository,
        FakeClock(now),
        SEOUL,
    )

    assert service.run() == 2
    assert repository.calls == [
        (
            (
                RepurchaseTrigger(5, date(2026, 8, 19)),
                RepurchaseTrigger(3, date(2026, 8, 17)),
                RepurchaseTrigger(1, date(2026, 8, 15)),
            ),
            now,
            now,
        )
    ]


def test_late_same_day_keeps_nine_as_schedule_and_current_creation_time() -> None:
    now = datetime(2026, 8, 14, 1, 37, tzinfo=UTC)
    repository = StubRepository()
    service = RepurchaseNotificationService(
        repository,
        FakeClock(now),
        SEOUL,
    )

    service.run()

    _, scheduled_at, created_at = repository.calls[0]
    assert scheduled_at == datetime(2026, 8, 14, 0, 0, tzinfo=UTC)
    assert created_at == now


def test_repository_failure_uses_worker_domain_error() -> None:
    service = RepurchaseNotificationService(
        StubRepository(fails=True),
        FakeClock(datetime(2026, 8, 14, 0, 0, tzinfo=UTC)),
        SEOUL,
    )

    with pytest.raises(RepurchaseNotificationError):
        service.run()
