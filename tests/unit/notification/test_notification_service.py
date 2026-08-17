from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.notification.repository import (
    NotificationListRecord,
    NotificationPageRecord,
    NotificationPersistenceError,
    NotificationReadRecord,
    NotificationRepository,
)
from yeongyangkkuk.notification.service import NotificationService
from yeongyangkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.9")]

NOW = datetime(2026, 8, 14, 0, 30, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000390")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000390")
NOTIFICATION_ID = UUID("41000000-0000-4000-8000-000000000390")


class StubNotificationRepository(NotificationRepository):
    def __init__(self) -> None:
        self.fails = False
        self.read_result: NotificationReadRecord | None = NotificationReadRecord(
            id=NOTIFICATION_ID,
            read_at=NOW,
        )
        self.list_calls: list[tuple[UUID, int, int]] = []
        self.read_calls: list[tuple[UUID, UUID, datetime]] = []

    def list_for_user(
        self, *, user_id: UUID, page: int, page_size: int
    ) -> NotificationPageRecord:
        self.list_calls.append((user_id, page, page_size))
        if self.fails:
            raise NotificationPersistenceError
        return NotificationPageRecord(
            items=(
                NotificationListRecord(
                    id=NOTIFICATION_ID,
                    care_item_id=ITEM_ID,
                    product_name="알림 제품",
                    notification_type="EXPIRATION",
                    reference_date=date(2026, 8, 19),
                    trigger_days_before=5,
                    scheduled_at=datetime(2026, 8, 14, 0, 0, tzinfo=UTC),
                    created_at=NOW,
                    read_at=None,
                ),
            ),
            total=1,
        )

    def mark_read(
        self, *, user_id: UUID, notification_id: UUID, read_at: datetime
    ) -> NotificationReadRecord | None:
        self.read_calls.append((user_id, notification_id, read_at))
        if self.fails:
            raise NotificationPersistenceError
        return self.read_result


def test_lists_notification_page_and_derives_read_state() -> None:
    repository = StubNotificationRepository()
    service = NotificationService(repository, FakeClock(NOW))

    result = service.list_notifications(user_id=USER_ID, page=1, page_size=20)

    assert repository.list_calls == [(USER_ID, 1, 20)]
    assert result.total == 1
    assert result.has_next is False
    assert result.items[0].is_read is False
    assert result.items[0].product_name == "알림 제품"


def test_marks_owned_notification_read_with_injected_time() -> None:
    repository = StubNotificationRepository()
    service = NotificationService(repository, FakeClock(NOW))

    result = service.mark_read(user_id=USER_ID, notification_id=NOTIFICATION_ID)

    assert result.read_at == NOW
    assert repository.read_calls == [(USER_ID, NOTIFICATION_ID, NOW)]


def test_missing_or_other_notification_is_hidden_as_not_found() -> None:
    repository = StubNotificationRepository()
    repository.read_result = None
    service = NotificationService(repository, FakeClock(NOW))

    with pytest.raises(AppError) as error:
        service.mark_read(user_id=USER_ID, notification_id=NOTIFICATION_ID)

    assert error.value.status_code == 404
    assert error.value.code == "NOTIFICATION_NOT_FOUND"


@pytest.mark.parametrize("operation", ["list", "read"])
def test_repository_failure_becomes_service_unavailable(operation: str) -> None:
    repository = StubNotificationRepository()
    repository.fails = True
    service = NotificationService(repository, FakeClock(NOW))

    with pytest.raises(AppError) as error:
        if operation == "list":
            service.list_notifications(user_id=USER_ID, page=1, page_size=20)
        else:
            service.mark_read(user_id=USER_ID, notification_id=NOTIFICATION_ID)

    assert error.value.status_code == 503
    assert error.value.code == "SERVICE_UNAVAILABLE"
