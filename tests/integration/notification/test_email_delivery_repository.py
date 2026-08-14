from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from allyakkkuk.auth.models import User, UserStatus
from allyakkkuk.care.models import CareItem
from allyakkkuk.curation.models import Product
from allyakkkuk.db.session import SessionFactory
from allyakkkuk.notification.email_repository import (
    SQLAlchemyEmailDeliveryRepository,
)
from allyakkkuk.notification.models import EmailDelivery, Notification

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.12")]

SCHEDULED_AT = datetime(2026, 8, 14, 0, 0, tzinfo=UTC)
CREATED_AT = SCHEDULED_AT + timedelta(minutes=1)
USER_IDS = [UUID(f"11000000-0000-4000-8000-{value:012d}") for value in (415, 416, 417)]
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000415")
ITEM_IDS = [UUID(f"31000000-0000-4000-8000-{value:012d}") for value in (415, 416, 417)]
NOTIFICATION_IDS = [
    UUID(f"41000000-0000-4000-8000-{value:012d}") for value in (415, 416, 417)
]


@pytest.fixture(autouse=True)
def email_delivery_data() -> Iterator[None]:
    _clean()
    with SessionFactory.begin() as session:
        session.add_all(
            [
                _user(USER_IDS[0], "415", UserStatus.ACTIVE, verified=True),
                _user(USER_IDS[1], "416", UserStatus.ACTIVE, verified=False),
                _user(USER_IDS[2], "417", UserStatus.SUSPENDED, verified=True),
            ]
        )
        session.add(
            Product(
                id=PRODUCT_ID,
                sku="EMAIL-DELIVERY-415",
                product_type="SUPPLEMENT",
                brand="이메일 전달 통합",
                name="이메일 전달 통합 제품",
                image_url="/static/products/email-delivery-415.svg",
                unit_form="CAPSULE",
                units_per_package=Decimal("30"),
                display_price=0,
                is_published=False,
                sort_order=415,
                created_at=SCHEDULED_AT,
                updated_at=SCHEDULED_AT,
            )
        )
        session.flush()
        session.add_all(
            [
                _item(item_id, user_id)
                for item_id, user_id in zip(ITEM_IDS, USER_IDS, strict=True)
            ]
        )
        session.flush()
        session.add_all(
            [
                _notification(
                    NOTIFICATION_IDS[0],
                    USER_IDS[0],
                    ITEM_IDS[0],
                    scheduled_at=SCHEDULED_AT,
                ),
                _notification(
                    NOTIFICATION_IDS[1],
                    USER_IDS[1],
                    ITEM_IDS[1],
                    scheduled_at=SCHEDULED_AT,
                ),
                _notification(
                    NOTIFICATION_IDS[2],
                    USER_IDS[2],
                    ITEM_IDS[2],
                    scheduled_at=SCHEDULED_AT,
                ),
            ]
        )
    yield
    _clean()


def _user(
    user_id: UUID,
    suffix: str,
    status: UserStatus,
    *,
    verified: bool,
) -> User:
    return User(
        id=user_id,
        name=f"이메일 전달 사용자 {suffix}",
        login_id=f"EmailDelivery{suffix}",
        normalized_login_id=f"emaildelivery{suffix}",
        email=f"email-delivery-{suffix}@example.com",
        normalized_email=f"email-delivery-{suffix}@example.com",
        password_hash="not-a-real-password-hash",
        email_verified_at=SCHEDULED_AT if verified else None,
        status=status.value,
        created_at=SCHEDULED_AT,
        updated_at=SCHEDULED_AT,
    )


def _item(item_id: UUID, user_id: UUID) -> CareItem:
    return CareItem(
        id=item_id,
        user_id=user_id,
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


def _notification(
    notification_id: UUID,
    user_id: UUID,
    item_id: UUID,
    *,
    scheduled_at: datetime,
) -> Notification:
    return Notification(
        id=notification_id,
        user_id=user_id,
        care_item_id=item_id,
        notification_type="REPURCHASE",
        reference_date=date(2026, 8, 19),
        trigger_days_before=5,
        scheduled_at=scheduled_at,
        created_at=CREATED_AT,
    )


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
        session.execute(delete(CareItem).where(CareItem.id.in_(ITEM_IDS)))
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(User).where(User.id.in_(USER_IDS)))


def test_enqueue_claim_retry_and_sent_are_idempotent_with_attempt_token() -> None:
    claim_time = CREATED_AT
    retry_at = claim_time + timedelta(minutes=5)
    with SessionFactory() as session:
        repository = SQLAlchemyEmailDeliveryRepository(session)
        created = repository.enqueue_for_schedule(
            scheduled_at=SCHEDULED_AT,
            created_at=CREATED_AT,
        )
        repeated = repository.enqueue_for_schedule(
            scheduled_at=SCHEDULED_AT,
            created_at=CREATED_AT,
        )
        first_claim = repository.claim_due(
            now=claim_time,
            lease_until=retry_at,
            max_attempts=3,
        )
        concurrently_unavailable = repository.claim_due(
            now=claim_time,
            lease_until=retry_at,
            max_attempts=3,
        )
        assert first_claim is not None
        retry_status = repository.mark_failed(
            delivery_id=first_claim.id,
            attempt_count=first_claim.attempt_count,
            failed_at=claim_time,
            retry_at=retry_at,
            max_attempts=3,
            error_code="SMTP_DELIVERY_FAILED",
        )
        before_due = repository.claim_due(
            now=retry_at - timedelta(seconds=1),
            lease_until=retry_at + timedelta(minutes=5),
            max_attempts=3,
        )
        second_claim = repository.claim_due(
            now=retry_at,
            lease_until=retry_at + timedelta(minutes=5),
            max_attempts=3,
        )
        assert second_claim is not None
        stale_success = repository.mark_sent(
            delivery_id=second_claim.id,
            attempt_count=1,
            sent_at=retry_at,
        )
        sent = repository.mark_sent(
            delivery_id=second_claim.id,
            attempt_count=2,
            sent_at=retry_at,
        )
        after_sent = repository.claim_due(
            now=retry_at + timedelta(minutes=10),
            lease_until=retry_at + timedelta(minutes=15),
            max_attempts=3,
        )

    assert created == 1
    assert repeated == 0
    assert first_claim.recipient_email == "email-delivery-415@example.com"
    assert concurrently_unavailable is before_due is after_sent is None
    assert retry_status == "RETRY"
    assert second_claim.attempt_count == 2
    assert stale_success is False
    assert sent is True


def test_expired_third_sending_attempt_becomes_unknown_failure() -> None:
    with SessionFactory() as session:
        repository = SQLAlchemyEmailDeliveryRepository(session)
        repository.enqueue_for_schedule(
            scheduled_at=SCHEDULED_AT,
            created_at=CREATED_AT,
        )
        delivery = session.scalar(
            select(EmailDelivery).where(
                EmailDelivery.notification_id == NOTIFICATION_IDS[0]
            )
        )
        assert delivery is not None
        session.execute(
            update(EmailDelivery)
            .where(EmailDelivery.id == delivery.id)
            .values(
                status="SENDING",
                attempt_count=3,
                next_retry_at=CREATED_AT,
                sent_at=None,
                last_error=None,
                updated_at=CREATED_AT,
            )
        )
        session.commit()

        finalized = repository.finalize_expired_final_attempts(
            now=CREATED_AT,
            max_attempts=3,
        )
        session.refresh(delivery)

    assert finalized == 1
    assert delivery.status == "FAILED"
    assert delivery.last_error == "DELIVERY_RESULT_UNKNOWN"
    assert delivery.next_retry_at is None


def test_database_rejects_state_inconsistent_delivery() -> None:
    with SessionFactory() as session:
        session.add(
            EmailDelivery(
                notification_id=NOTIFICATION_IDS[0],
                recipient_email="invalid@example.com",
                status="PENDING",
                attempt_count=1,
                next_retry_at=CREATED_AT,
                created_at=CREATED_AT,
                updated_at=CREATED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
