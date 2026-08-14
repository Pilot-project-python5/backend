from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import delete, select

from allyakkkuk.auth.models import User, UserStatus
from allyakkkuk.care.models import CareItem
from allyakkkuk.curation.models import Product
from allyakkkuk.db.session import SessionFactory
from allyakkkuk.notification.models import Notification
from allyakkkuk.notification.repository import (
    SQLAlchemyExpirationNotificationRepository,
)
from allyakkkuk.notification.service import ExpirationNotificationService
from allyakkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.9")]

NOW = datetime(2026, 8, 14, 1, 37, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000394")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000394")
OFFSETS = (5, 4, 3, 1)
ITEM_IDS = {
    offset: UUID(f"31000000-0000-4000-8000-{394 + offset:012d}") for offset in OFFSETS
}
NO_EXPIRATION_ID = UUID("31000000-0000-4000-8000-000000000410")
DELETED_ID = UUID("31000000-0000-4000-8000-000000000411")


@pytest.fixture(autouse=True)
def expiration_environment() -> Iterator[None]:
    _clean()
    with SessionFactory.begin() as session:
        session.add(
            User(
                id=USER_ID,
                name="유통기한 알림 인수 사용자",
                login_id="Expiration394",
                normalized_login_id="expiration394",
                email="expiration-394@example.com",
                normalized_email="expiration-394@example.com",
                password_hash="not-a-real-password-hash",
                email_verified_at=NOW,
                status=UserStatus.ACTIVE.value,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.add(
            Product(
                id=PRODUCT_ID,
                sku="EXPIRATION-394",
                product_type="SUPPLEMENT",
                brand="유통기한 알림 테스트",
                name="유통기한 알림 테스트 제품",
                image_url="/static/products/expiration-394.svg",
                unit_form="CAPSULE",
                units_per_package=Decimal("30"),
                display_price=0,
                is_published=False,
                sort_order=394,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.flush()
        session.add_all(
            [_item(ITEM_IDS[offset], offset) for offset in OFFSETS]
            + [
                _item(NO_EXPIRATION_ID, None),
                _item(DELETED_ID, 5, deleted_at=NOW),
            ]
        )
    yield
    _clean()


def _item(
    item_id: UUID,
    days_until_expiration: int | None,
    *,
    deleted_at: datetime | None = None,
) -> CareItem:
    return CareItem(
        id=item_id,
        user_id=USER_ID,
        product_id=PRODUCT_ID,
        purchase_date=date(2026, 8, 1),
        intake_start_date=date(2026, 8, 1),
        expected_depletion_date=date(2026, 9, 1),
        expiration_date=(
            date(2026, 8, 14) + timedelta(days=days_until_expiration)
            if days_until_expiration is not None
            else None
        ),
        total_quantity=Decimal("30"),
        quantity_unit="CAPSULE",
        dose_per_intake=Decimal("1"),
        intakes_per_day=1,
        created_at=NOW,
        updated_at=NOW,
        deleted_at=deleted_at,
    )


def _clean() -> None:
    with SessionFactory.begin() as session:
        session.execute(delete(Notification).where(Notification.user_id == USER_ID))
        session.execute(delete(CareItem).where(CareItem.user_id == USER_ID))
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(User).where(User.id == USER_ID))


def test_worker_creates_only_expiration_triggers_once() -> None:
    with SessionFactory() as session:
        service = ExpirationNotificationService(
            SQLAlchemyExpirationNotificationRepository(session),
            FakeClock(NOW),
            ZoneInfo("Asia/Seoul"),
        )
        first_created = service.run()
        repeated_created = service.run()

    assert first_created == 3
    assert repeated_created == 0
    with SessionFactory() as session:
        notifications = tuple(
            session.scalars(
                select(Notification).order_by(Notification.trigger_days_before.desc())
            )
        )

    assert [item.trigger_days_before for item in notifications] == [5, 3, 1]
    assert {item.care_item_id for item in notifications} == {
        ITEM_IDS[5],
        ITEM_IDS[3],
        ITEM_IDS[1],
    }
    assert all(item.notification_type == "EXPIRATION" for item in notifications)
    assert all(
        item.scheduled_at == datetime(2026, 8, 14, 0, 0, tzinfo=UTC)
        for item in notifications
    )
