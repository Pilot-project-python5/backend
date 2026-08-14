"""논리 알림 생성과 화면 조회·읽음 서비스."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from allyakkkuk.core.errors import AppError
from allyakkkuk.notification.repository import (
    ExpirationNotificationRepository,
    NotificationListRecord,
    NotificationPersistenceError,
    NotificationRepository,
    NotificationTrigger,
    RepurchaseNotificationRepository,
)
from allyakkkuk.ports.clock import Clock

TRIGGER_DAYS = (5, 3, 1)
LOCAL_TRIGGER_TIME = time(9, 0)


class RepurchaseNotificationError(Exception):
    pass


class ExpirationNotificationError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class NotificationListItem:
    id: UUID
    care_item_id: UUID
    product_name: str
    notification_type: str
    reference_date: date
    trigger_days_before: int
    scheduled_at: datetime
    created_at: datetime
    read_at: datetime | None
    is_read: bool


@dataclass(frozen=True, slots=True)
class NotificationListResult:
    items: tuple[NotificationListItem, ...]
    page: int
    page_size: int
    total: int
    has_next: bool


@dataclass(frozen=True, slots=True)
class NotificationReadResult:
    id: UUID
    read_at: datetime


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
            NotificationTrigger(
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


class ExpirationNotificationService:
    def __init__(
        self,
        repository: ExpirationNotificationRepository,
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
            NotificationTrigger(
                days_before=days_before,
                reference_date=local_now.date() + timedelta(days=days_before),
            )
            for days_before in TRIGGER_DAYS
        )
        try:
            return self._repository.create_expiration_notifications(
                triggers=triggers,
                scheduled_at=local_schedule.astimezone(UTC),
                created_at=now,
            )
        except NotificationPersistenceError as exc:
            raise ExpirationNotificationError from exc


class NotificationService:
    def __init__(self, repository: NotificationRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    def list_notifications(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
    ) -> NotificationListResult:
        try:
            result = self._repository.list_for_user(
                user_id=user_id,
                page=page,
                page_size=page_size,
            )
        except NotificationPersistenceError as exc:
            raise _service_unavailable() from exc
        return NotificationListResult(
            items=tuple(_list_item(item) for item in result.items),
            page=page,
            page_size=page_size,
            total=result.total,
            has_next=page * page_size < result.total,
        )

    def mark_read(
        self,
        *,
        user_id: UUID,
        notification_id: UUID,
    ) -> NotificationReadResult:
        try:
            result = self._repository.mark_read(
                user_id=user_id,
                notification_id=notification_id,
                read_at=self._clock.now(),
            )
        except NotificationPersistenceError as exc:
            raise _service_unavailable() from exc
        if result is None:
            raise AppError(
                status_code=404,
                code="NOTIFICATION_NOT_FOUND",
                message="알림을 찾을 수 없습니다.",
            )
        return NotificationReadResult(id=result.id, read_at=result.read_at)


def _list_item(record: NotificationListRecord) -> NotificationListItem:
    return NotificationListItem(
        id=record.id,
        care_item_id=record.care_item_id,
        product_name=record.product_name,
        notification_type=record.notification_type,
        reference_date=record.reference_date,
        trigger_days_before=record.trigger_days_before,
        scheduled_at=record.scheduled_at,
        created_at=record.created_at,
        read_at=record.read_at,
        is_read=record.read_at is not None,
    )


def _service_unavailable() -> AppError:
    return AppError(
        status_code=503,
        code="SERVICE_UNAVAILABLE",
        message="서비스가 아직 준비되지 않았습니다.",
    )
