"""재구매 논리 알림 생성 서비스."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from allyakkkuk.notification.repository import (
    NotificationPersistenceError,
    RepurchaseNotificationRepository,
    RepurchaseTrigger,
)
from allyakkkuk.ports.clock import Clock

TRIGGER_DAYS = (5, 3, 1)
LOCAL_TRIGGER_TIME = time(9, 0)


class RepurchaseNotificationError(Exception):
    pass


class RepurchaseNotificationService:
    def __init__(
        self,
        repository: RepurchaseNotificationRepository,
        clock: Clock,
        time_zone: ZoneInfo,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._time_zone = time_zone

    def run(self) -> int:
        now = self._clock.now()
        local_now = now.astimezone(self._time_zone)
        local_schedule = datetime.combine(
            local_now.date(),
            LOCAL_TRIGGER_TIME,
            tzinfo=self._time_zone,
        )
        if local_now < local_schedule:
            return 0

        triggers = tuple(
            RepurchaseTrigger(
                days_before=days_before,
                reference_date=local_now.date() + timedelta(days=days_before),
            )
            for days_before in TRIGGER_DAYS
        )
        try:
            return self._repository.create_repurchase_notifications(
                triggers=triggers,
                scheduled_at=local_schedule.astimezone(UTC),
                created_at=now,
            )
        except NotificationPersistenceError as exc:
            raise RepurchaseNotificationError from exc
