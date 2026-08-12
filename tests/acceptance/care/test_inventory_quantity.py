from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from allyakkkuk.auth.current_user_dependencies import require_current_user
from allyakkkuk.auth.current_user_service import AuthenticatedUser
from allyakkkuk.auth.models import Gender, User, UserStatus
from allyakkkuk.care.care_item_repository import SQLAlchemyCareItemRepository
from allyakkkuk.care.care_item_router import get_care_item_service
from allyakkkuk.care.care_item_service import CareItemService
from allyakkkuk.care.models import CareItem
from allyakkkuk.curation.models import Product
from allyakkkuk.db.session import SessionFactory, get_db_session
from allyakkkuk.main import app
from allyakkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.3")]

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000209")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000209")


def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=USER_ID,
        login_id="Inventory209",
        name="구매 수량 인수 사용자",
        email="inventory-209@example.com",
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
def inventory_environment() -> Iterator[None]:
    clock = FakeClock(NOW)

    def care_service(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> CareItemService:
        return CareItemService(
            SQLAlchemyCareItemRepository(session),
            clock,
            ZoneInfo("Asia/Seoul"),
        )

    app.dependency_overrides[require_current_user] = current_user
    app.dependency_overrides[get_care_item_service] = care_service
    _clean_data()
    with SessionFactory.begin() as session:
        session.add(
            User(
                id=USER_ID,
                name="구매 수량 인수 사용자",
                login_id="Inventory209",
                normalized_login_id="inventory209",
                email="inventory-209@example.com",
                normalized_email="inventory-209@example.com",
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
                sku="INVENTORY-ACCEPT-209",
                product_type="MEDICATION",
                brand="구매 수량 인수 브랜드",
                name="구매 수량 인수 제품",
                image_url="/static/products/inventory-accept-209.svg",
                unit_form="PACKET",
                units_per_package=Decimal("30"),
                display_price=10000,
                is_published=False,
                sort_order=209,
                created_at=NOW,
                updated_at=NOW,
            )
        )
    yield
    app.dependency_overrides.pop(require_current_user, None)
    app.dependency_overrides.pop(get_care_item_service, None)
    _clean_data()


def _clean_data() -> None:
    with SessionFactory.begin() as session:
        session.execute(delete(CareItem).where(CareItem.user_id == USER_ID))
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(User).where(User.id == USER_ID))


def test_repurchase_returns_catalog_unit_without_merging_existing_quantity() -> None:
    first_payload = {
        "product_id": str(PRODUCT_ID),
        "purchase_date": "2026-08-10",
        "intake_start_date": "2026-08-12",
        "total_quantity": "30",
        "quantity_unit": "TABLET",
        "dose_per_intake": "1",
        "intakes_per_day": 2,
    }
    with TestClient(app) as client:
        first = client.post("/api/v1/care/items", json=first_payload)

        with SessionFactory.begin() as session:
            session.execute(
                update(Product)
                .where(Product.id == PRODUCT_ID)
                .values(unit_form="CAPSULE")
            )

        second = client.post(
            "/api/v1/care/items",
            json={**first_payload, "total_quantity": "60"},
        )

    assert first.status_code == second.status_code == 201
    assert first.json()["quantity_unit"] == "PACKET"
    assert second.json()["quantity_unit"] == "CAPSULE"
    assert first.json()["id"] != second.json()["id"]

    with SessionFactory() as session:
        stored = {
            str(item.id): item
            for item in session.scalars(
                select(CareItem).where(CareItem.user_id == USER_ID)
            )
        }
    assert stored[first.json()["id"]].total_quantity == Decimal("30")
    assert stored[first.json()["id"]].quantity_unit == "PACKET"
    assert stored[second.json()["id"]].total_quantity == Decimal("60")
    assert stored[second.json()["id"]].quantity_unit == "CAPSULE"
