from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from allyakkkuk.notification.repository import (
    ExpirationNotificationRepository,
    NotificationPersistenceError,
    NotificationTrigger,
)
from allyakkkuk.notification.service import (
    ExpirationNotificationError,
    ExpirationNotificationService,
)
from allyakkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.9")]

SEOUL = ZoneInfo("Asia/Seoul")


class StubExpirationRepository(ExpirationNotificationRepository):
    def __init__(self, *, created: int = 3, fails: bool = False) -> None:
        self.created = created
        self.fails = fails
        self.calls: list[
            tuple[tuple[NotificationTrigger, ...], datetime, datetime]
        ] = []

    def create_expiration_notifications(
        self,
        *,
        triggers: tuple[NotificationTrigger, ...],
        scheduled_at: datetime,
        created_at: datetime,
    ) -> int:
        self.calls.append((triggers, scheduled_at, created_at))
        if self.fails:
            raise NotificationPersistenceError
        return self.created


def test_expiration_before_local_nine_does_not_query_repository() -> None:
    repository = StubExpirationRepository()
    service = ExpirationNotificationService(
        repository,
        FakeClock(datetime(2026, 8, 13, 23, 59, 59, tzinfo=UTC)),
        SEOUL,
    )

    assert service.run() == 0
    assert repository.calls == []


def test_expiration_at_local_nine_creates_exact_trigger_dates() -> None:
    now = datetime(2026, 8, 14, 0, 0, tzinfo=UTC)
    repository = StubExpirationRepository(created=2)
    service = ExpirationNotificationService(repository, FakeClock(now), SEOUL)

    assert service.run() == 2
    assert repository.calls == [
        (
            (
                NotificationTrigger(5, date(2026, 8, 19)),
                NotificationTrigger(3, date(2026, 8, 17)),
                NotificationTrigger(1, date(2026, 8, 15)),
            ),
            now,
            now,
        )
    ]


def test_expiration_repository_failure_uses_worker_domain_error() -> None:
    service = ExpirationNotificationService(
        StubExpirationRepository(fails=True),
        FakeClock(datetime(2026, 8, 14, 0, 0, tzinfo=UTC)),
        SEOUL,
    )

    with pytest.raises(ExpirationNotificationError):
        service.run()
