from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import delete, select

from yeongyangkkuk.adapters.email import FakeEmailSender
from yeongyangkkuk.auth.models import User, UserStatus
from yeongyangkkuk.care.models import CareItem
from yeongyangkkuk.curation.models import Product
from yeongyangkkuk.db.session import SessionFactory
from yeongyangkkuk.notification.email_repository import (
    SQLAlchemyEmailDeliveryRepository,
)
from yeongyangkkuk.notification.email_service import EmailReminderService
from yeongyangkkuk.notification.models import EmailDelivery, Notification
from yeongyangkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.12")]

SCHEDULED_AT = datetime(2026, 8, 14, 0, 0, tzinfo=UTC)
NOW = SCHEDULED_AT + timedelta(minutes=2)
USER_ID = UUID("11000000-0000-4000-8000-000000000418")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000418")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000418")
NOTIFICATION_IDS = (
    UUID("41000000-0000-4000-8000-000000000418"),
    UUID("41000000-0000-4000-8000-000000000419"),
)


@pytest.fixture(autouse=True)
def email_reminder_data() -> Iterator[None]:
    _clean()
    with SessionFactory.begin() as session:
        session.add(
            User(
                id=USER_ID,
                name="이메일 리마인더 인수 사용자",
                login_id="EmailReminder418",
                normalized_login_id="emailreminder418",
                email="email-reminder-418@example.com",
                normalized_email="email-reminder-418@example.com",
                password_hash="not-a-real-password-hash",
                email_verified_at=SCHEDULED_AT,
                status=UserStatus.ACTIVE.value,
                created_at=SCHEDULED_AT,
                updated_at=SCHEDULED_AT,
            )
        )
        session.add(
            Product(
                id=PRODUCT_ID,
                sku="EMAIL-REMINDER-418",
                product_type="SUPPLEMENT",
                brand="이메일 리마인더 인수",
                name="이메일 리마인더 인수 제품",
                image_url="/static/products/email-reminder-418.svg",
                unit_form="CAPSULE",
                units_per_package=Decimal("30"),
                display_price=0,
                is_published=False,
                sort_order=418,
                created_at=SCHEDULED_AT,
                updated_at=SCHEDULED_AT,
            )
        )
        session.flush()
        session.add(
            CareItem(
                id=ITEM_ID,
                user_id=USER_ID,
                product_id=PRODUCT_ID,
                purchase_date=date(2026, 8, 1),
                intake_start_date=date(2026, 8, 1),
                expected_depletion_date=date(2026, 8, 19),
                expiration_date=date(2026, 8, 19),
                total_quantity=Decimal("30"),
                quantity_unit="CAPSULE",
                dose_per_intake=Decimal("1"),
                intakes_per_day=1,
                created_at=SCHEDULED_AT,
                updated_at=SCHEDULED_AT,
            )
        )
        session.flush()
        session.add_all(
            [
                Notification(
                    id=NOTIFICATION_IDS[0],
                    user_id=USER_ID,
                    care_item_id=ITEM_ID,
                    notification_type="REPURCHASE",
                    reference_date=date(2026, 8, 19),
                    trigger_days_before=5,
                    scheduled_at=SCHEDULED_AT,
                    created_at=SCHEDULED_AT + timedelta(minutes=1),
                ),
                Notification(
                    id=NOTIFICATION_IDS[1],
                    user_id=USER_ID,
                    care_item_id=ITEM_ID,
                    notification_type="EXPIRATION",
                    reference_date=date(2026, 8, 19),
                    trigger_days_before=5,
                    scheduled_at=SCHEDULED_AT,
                    created_at=SCHEDULED_AT + timedelta(minutes=1),
                ),
            ]
        )
    yield
    _clean()


def _clean() -> None:
    with SessionFactory.begin() as session:
        session.execute(
            delete(EmailDelivery).where(
                EmailDelivery.notification_id.in_(NOTIFICATION_IDS)
            )
        )
        session.execute(
            delete(Notification).where(Notification.id.in_(NOTIFICATION_IDS))
        )
        session.execute(delete(CareItem).where(CareItem.id == ITEM_ID))
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(User).where(User.id == USER_ID))


def test_worker_sends_each_logical_event_once_and_preserves_success() -> None:
    sender = FakeEmailSender()
    with SessionFactory() as session:
        service = EmailReminderService(
            SQLAlchemyEmailDeliveryRepository(session),
            sender,
            FakeClock(NOW),
            ZoneInfo("Asia/Seoul"),
        )
        first = service.run()
        repeated = service.run()

    assert first.enqueued == first.sent == 2
    assert first.retry_scheduled == first.failed == 0
    assert repeated.enqueued == repeated.sent == 0
    assert len(sender.messages) == 2
    assert {message.recipients for message in sender.messages} == {
        ("email-reminder-418@example.com",)
    }
    assert any("재구매가 5일" in message.subject for message in sender.messages)
    assert any("유통기한이 5일" in message.subject for message in sender.messages)

    with SessionFactory() as session:
        deliveries = tuple(
            session.scalars(
                select(EmailDelivery).order_by(EmailDelivery.notification_id)
            )
        )
    owned_deliveries = [
        item for item in deliveries if item.notification_id in NOTIFICATION_IDS
    ]
    assert len(owned_deliveries) == 2
    assert all(item.status == "SENT" for item in owned_deliveries)
    assert all(item.attempt_count == 1 for item in owned_deliveries)
    assert all(item.sent_at == NOW for item in owned_deliveries)
    assert all(item.next_retry_at is None for item in owned_deliveries)
