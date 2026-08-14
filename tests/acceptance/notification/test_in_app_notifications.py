from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import UUID

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from allyakkkuk.auth.current_user_dependencies import require_current_user
from allyakkkuk.auth.current_user_service import AuthenticatedUser
from allyakkkuk.auth.models import Gender, User, UserStatus
from allyakkkuk.care.models import CareItem
from allyakkkuk.curation.models import Product
from allyakkkuk.db.session import SessionFactory, get_db_session
from allyakkkuk.main import app
from allyakkkuk.notification.models import Notification
from allyakkkuk.notification.repository import SQLAlchemyNotificationRepository
from allyakkkuk.notification.router import get_notification_service
from allyakkkuk.notification.service import NotificationService
from allyakkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.9")]

NOW = datetime(2026, 8, 14, 0, 30, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000395")
OTHER_USER_ID = UUID("11000000-0000-4000-8000-000000000396")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000395")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000395")
OTHER_ITEM_ID = UUID("31000000-0000-4000-8000-000000000396")
FIRST_ID = UUID("41000000-0000-4000-8000-000000000395")
LATEST_ID = UUID("41000000-0000-4000-8000-000000000396")
OTHER_ID = UUID("41000000-0000-4000-8000-000000000397")
MISSING_ID = UUID("41000000-0000-4000-8000-000000000399")


def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=USER_ID,
        login_id="Notification395",
        name="화면 알림 인수 사용자",
        email="notification-395@example.com",
        status=UserStatus.ACTIVE,
        email_verified_at=NOW,
        birth_date=date(1995, 5, 20),
        gender=Gender.FEMALE,
        height_cm=Decimal("165"),
        weight_kg=Decimal("55"),
        access_token_expires_at=NOW,
        refresh_token_expires_at=NOW,
    )


@pytest.fixture(autouse=True)
def in_app_notification_environment() -> Iterator[None]:
    def notification_service(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> NotificationService:
        return NotificationService(
            SQLAlchemyNotificationRepository(session),
            FakeClock(NOW + timedelta(minutes=5)),
        )

    app.dependency_overrides[require_current_user] = current_user
    app.dependency_overrides[get_notification_service] = notification_service
    _clean()
    _seed()
    yield
    app.dependency_overrides.pop(require_current_user, None)
    app.dependency_overrides.pop(get_notification_service, None)
    _clean()


def _seed() -> None:
    with SessionFactory.begin() as session:
        session.add_all([_user(USER_ID, "395"), _user(OTHER_USER_ID, "396")])
        session.add(
            Product(
                id=PRODUCT_ID,
                sku="NOTIFICATION-ACCEPT-395",
                product_type="SUPPLEMENT",
                brand="화면 알림 인수 브랜드",
                name="화면 알림 인수 제품",
                image_url="/static/products/notification-395.svg",
                unit_form="CAPSULE",
                units_per_package=Decimal("30"),
                display_price=0,
                is_published=False,
                sort_order=395,
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
                    FIRST_ID,
                    USER_ID,
                    ITEM_ID,
                    "REPURCHASE",
                    date(2026, 8, 19),
                    NOW,
                    5,
                ),
                _notification(
                    LATEST_ID,
                    USER_ID,
                    ITEM_ID,
                    "EXPIRATION",
                    date(2026, 8, 17),
                    NOW + timedelta(minutes=1),
                    3,
                ),
                _notification(
                    OTHER_ID,
                    OTHER_USER_ID,
                    OTHER_ITEM_ID,
                    "REPURCHASE",
                    date(2026, 8, 19),
                    NOW,
                    5,
                ),
            ]
        )


def _user(user_id: UUID, suffix: str) -> User:
    return User(
        id=user_id,
        name=f"화면 알림 인수 사용자 {suffix}",
        login_id=f"NotifAcc{suffix}",
        normalized_login_id=f"notifacc{suffix}",
        email=f"notification-accept-{suffix}@example.com",
        normalized_email=f"notification-accept-{suffix}@example.com",
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
    notification_type: str,
    reference_date: date,
    created_at: datetime,
    trigger_days_before: int,
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


def test_user_lists_only_owned_notifications_including_deleted_item_history() -> None:
    with TestClient(app) as client:
        first_page = client.get(
            "/api/v1/notifications", params={"page": 1, "page_size": 1}
        )
        second_page = client.get(
            "/api/v1/notifications", params={"page": 2, "page_size": 1}
        )

    assert first_page.status_code == second_page.status_code == 200
    assert first_page.headers["cache-control"] == "no-store"
    assert first_page.json()["total"] == second_page.json()["total"] == 2
    assert first_page.json()["has_next"] is True
    assert [item["id"] for item in first_page.json()["items"]] == [str(LATEST_ID)]
    assert [item["id"] for item in second_page.json()["items"]] == [str(FIRST_ID)]
    assert first_page.json()["items"][0]["product_name"] == "화면 알림 인수 제품"
    assert "user_id" not in first_page.text


def test_user_marks_owned_notification_once_and_cannot_probe_other_user() -> None:
    with TestClient(app) as client:
        first = client.put(f"/api/v1/notifications/{FIRST_ID}/read")
        repeated = client.put(f"/api/v1/notifications/{FIRST_ID}/read")
        other = client.put(f"/api/v1/notifications/{OTHER_ID}/read")
        missing = client.put(f"/api/v1/notifications/{MISSING_ID}/read")

    assert first.status_code == repeated.status_code == 200
    assert first.json() == repeated.json()
    assert first.json()["read_at"] == "2026-08-14T00:35:00Z"
    assert other.status_code == missing.status_code == 404
    assert other.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"
    assert missing.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"
