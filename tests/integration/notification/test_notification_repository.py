from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import delete

from allyakkkuk.auth.models import User, UserStatus
from allyakkkuk.care.models import CareItem
from allyakkkuk.curation.models import Product
from allyakkkuk.db.session import SessionFactory
from allyakkkuk.notification.models import Notification
from allyakkkuk.notification.repository import SQLAlchemyNotificationRepository

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.9")]

NOW = datetime(2026, 8, 14, 0, 30, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000392")
OTHER_USER_ID = UUID("11000000-0000-4000-8000-000000000393")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000392")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000392")
OTHER_ITEM_ID = UUID("31000000-0000-4000-8000-000000000393")
FIRST_NOTIFICATION_ID = UUID("41000000-0000-4000-8000-000000000392")
LATEST_NOTIFICATION_ID = UUID("41000000-0000-4000-8000-000000000393")
OTHER_NOTIFICATION_ID = UUID("41000000-0000-4000-8000-000000000394")
MISSING_NOTIFICATION_ID = UUID("41000000-0000-4000-8000-000000000399")


@pytest.fixture(autouse=True)
def notification_data() -> Iterator[None]:
    _clean()
    with SessionFactory.begin() as session:
        session.add_all([_user(USER_ID, "392"), _user(OTHER_USER_ID, "393")])
        session.add(
            Product(
                id=PRODUCT_ID,
                sku="NOTIFICATION-392",
                product_type="SUPPLEMENT",
                brand="화면 알림 통합 브랜드",
                name="화면 알림 통합 제품",
                image_url="/static/products/notification-392.svg",
                unit_form="CAPSULE",
                units_per_package=Decimal("30"),
                display_price=0,
                is_published=False,
                sort_order=392,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.flush()
        session.add_all(
            [
                _item(ITEM_ID, USER_ID, deleted_at=NOW),
                _item(OTHER_ITEM_ID, OTHER_USER_ID),
            ]
        )
        session.flush()
        session.add_all(
            [
                _notification(
                    FIRST_NOTIFICATION_ID,
                    USER_ID,
                    ITEM_ID,
                    notification_type="REPURCHASE",
                    reference_date=date(2026, 8, 19),
                    created_at=NOW,
                ),
                _notification(
                    LATEST_NOTIFICATION_ID,
                    USER_ID,
                    ITEM_ID,
                    notification_type="EXPIRATION",
                    reference_date=date(2026, 8, 17),
                    created_at=NOW,
                    trigger_days_before=3,
                ),
                _notification(
                    OTHER_NOTIFICATION_ID,
                    OTHER_USER_ID,
                    OTHER_ITEM_ID,
                    notification_type="REPURCHASE",
                    reference_date=date(2026, 8, 19),
                    created_at=NOW,
                ),
            ]
        )
    yield
    _clean()


def _user(user_id: UUID, suffix: str) -> User:
    return User(
        id=user_id,
        name=f"화면 알림 사용자 {suffix}",
        login_id=f"Notification{suffix}",
        normalized_login_id=f"notification{suffix}",
        email=f"notification-{suffix}@example.com",
        normalized_email=f"notification-{suffix}@example.com",
        password_hash="not-a-real-password-hash",
        email_verified_at=NOW,
        status=UserStatus.ACTIVE.value,
        created_at=NOW,
        updated_at=NOW,
    )


def _item(
    item_id: UUID, user_id: UUID, *, deleted_at: datetime | None = None
) -> CareItem:
    return CareItem(
        id=item_id,
        user_id=user_id,
        product_id=PRODUCT_ID,
        purchase_date=date(2026, 8, 1),
        intake_start_date=date(2026, 8, 1),
        expected_depletion_date=date(2026, 8, 19),
        expiration_date=date(2026, 8, 17),
        total_quantity=Decimal("30"),
        quantity_unit="CAPSULE",
        dose_per_intake=Decimal("1"),
        intakes_per_day=1,
        created_at=NOW,
        updated_at=NOW,
        deleted_at=deleted_at,
    )


def _notification(
    notification_id: UUID,
    user_id: UUID,
    item_id: UUID,
    *,
    notification_type: str,
    reference_date: date,
    created_at: datetime,
    trigger_days_before: int = 5,
) -> Notification:
    return Notification(
        id=notification_id,
        user_id=user_id,
        care_item_id=item_id,
        notification_type=notification_type,
        reference_date=reference_date,
        trigger_days_before=trigger_days_before,
        scheduled_at=NOW - timedelta(minutes=30),
        created_at=created_at,
    )


def _clean() -> None:
    with SessionFactory.begin() as session:
        session.execute(
            delete(Notification).where(
                Notification.user_id.in_([USER_ID, OTHER_USER_ID])
            )
        )
        session.execute(
            delete(CareItem).where(CareItem.user_id.in_([USER_ID, OTHER_USER_ID]))
        )
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(User).where(User.id.in_([USER_ID, OTHER_USER_ID])))


def test_lists_owned_notifications_with_stable_order_and_deleted_item_history() -> None:
    with SessionFactory() as session:
        repository = SQLAlchemyNotificationRepository(session)
        first = repository.list_for_user(user_id=USER_ID, page=1, page_size=1)
        second = repository.list_for_user(user_id=USER_ID, page=2, page_size=1)
        empty = repository.list_for_user(user_id=USER_ID, page=3, page_size=1)

    assert first.total == second.total == empty.total == 2
    assert [item.id for item in first.items] == [LATEST_NOTIFICATION_ID]
    assert [item.id for item in second.items] == [FIRST_NOTIFICATION_ID]
    assert empty.items == ()
    assert first.items[0].product_name == "화면 알림 통합 제품"


def test_marks_only_owned_notification_read_and_preserves_first_time() -> None:
    first_read_at = NOW + timedelta(minutes=1)
    with SessionFactory() as session:
        repository = SQLAlchemyNotificationRepository(session)
        first = repository.mark_read(
            user_id=USER_ID,
            notification_id=FIRST_NOTIFICATION_ID,
            read_at=first_read_at,
        )
        repeated = repository.mark_read(
            user_id=USER_ID,
            notification_id=FIRST_NOTIFICATION_ID,
            read_at=NOW + timedelta(minutes=2),
        )
        other = repository.mark_read(
            user_id=USER_ID,
            notification_id=OTHER_NOTIFICATION_ID,
            read_at=NOW + timedelta(minutes=2),
        )
        missing = repository.mark_read(
            user_id=USER_ID,
            notification_id=MISSING_NOTIFICATION_ID,
            read_at=NOW + timedelta(minutes=2),
        )

    assert first is not None and repeated is not None
    assert first.read_at == repeated.read_at == first_read_at
    assert other is missing is None
