from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from allyakkkuk.auth.current_user_dependencies import require_current_user
from allyakkkuk.auth.current_user_service import AuthenticatedUser
from allyakkkuk.auth.models import Gender, User, UserStatus
from allyakkkuk.care.care_item_repository import SQLAlchemyCareItemRepository
from allyakkkuk.care.care_item_router import get_care_item_management_service
from allyakkkuk.care.care_item_service import CareItemManagementService
from allyakkkuk.care.models import CareItem, CareNutrientSnapshot
from allyakkkuk.curation.models import Nutrient, Product
from allyakkkuk.db.session import SessionFactory, get_db_session
from allyakkkuk.main import app
from allyakkkuk.ports.clock import FakeClock

pytestmark = [
    pytest.mark.integration,
    pytest.mark.feature("F-3.4"),
    pytest.mark.feature("F-3.7"),
]

NOW = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000219")
OTHER_USER_ID = UUID("11000000-0000-4000-8000-000000000220")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000219")
NUTRIENT_ID = UUID("23000000-0000-4000-8000-000000000219")
FIRST_ID = UUID("31000000-0000-4000-8000-000000000221")
LATEST_ID = UUID("31000000-0000-4000-8000-000000000222")
DELETED_ID = UUID("31000000-0000-4000-8000-000000000223")
OTHER_ID = UUID("31000000-0000-4000-8000-000000000224")
MISSING_ID = UUID("31000000-0000-4000-8000-000000000299")
SNAPSHOT_ID = UUID("32000000-0000-4000-8000-000000000219")


def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=USER_ID,
        login_id="CareAccept219",
        name="복용 관리 인수 사용자",
        email="care-accept-219@example.com",
        status=UserStatus.ACTIVE,
        email_verified_at=NOW,
        birth_date=date(1995, 5, 20),
        gender=Gender.MALE,
        height_cm=Decimal("175"),
        weight_kg=Decimal("70"),
        access_token_expires_at=NOW,
        refresh_token_expires_at=NOW,
    )


@pytest.fixture(autouse=True)
def care_management_environment() -> Iterator[None]:
    clock = FakeClock(NOW)

    def management_service(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> CareItemManagementService:
        return CareItemManagementService(
            SQLAlchemyCareItemRepository(session),
            clock,
            ZoneInfo("Asia/Seoul"),
        )

    app.dependency_overrides[require_current_user] = current_user
    app.dependency_overrides[get_care_item_management_service] = management_service
    _clean_data()
    _seed_data()
    yield
    app.dependency_overrides.pop(require_current_user, None)
    app.dependency_overrides.pop(get_care_item_management_service, None)
    _clean_data()


def _clean_data() -> None:
    with SessionFactory.begin() as session:
        session.execute(
            delete(CareItem).where(CareItem.user_id.in_([USER_ID, OTHER_USER_ID]))
        )
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(Nutrient).where(Nutrient.id == NUTRIENT_ID))
        session.execute(delete(User).where(User.id.in_([USER_ID, OTHER_USER_ID])))


def _seed_data() -> None:
    with SessionFactory.begin() as session:
        for user_id, suffix in ((USER_ID, "219"), (OTHER_USER_ID, "220")):
            session.add(
                User(
                    id=user_id,
                    name=f"복용 관리 인수 사용자 {suffix}",
                    login_id=f"CareAccept{suffix}",
                    normalized_login_id=f"careaccept{suffix}",
                    email=f"care-accept-{suffix}@example.com",
                    normalized_email=f"care-accept-{suffix}@example.com",
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
                sku="CARE-ACCEPT-219",
                product_type="SUPPLEMENT",
                brand="복용 관리 인수 브랜드",
                name="복용 관리 비게시 제품",
                image_url="/static/products/care-accept-219.svg",
                unit_form="PACKET",
                units_per_package=Decimal("30"),
                display_price=0,
                is_published=False,
                sort_order=219,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.add(
            Nutrient(
                id=NUTRIENT_ID,
                code="CARE_ACCEPT_NUTRIENT_219",
                name="복용 관리 인수 성분",
                canonical_unit="MG",
                is_active=True,
            )
        )
        session.flush()
        session.add_all(
            [
                _item(FIRST_ID, USER_ID, NOW, Decimal("30")),
                _item(LATEST_ID, USER_ID, NOW, Decimal("60")),
                _item(
                    DELETED_ID,
                    USER_ID,
                    NOW - timedelta(minutes=2),
                    Decimal("90"),
                    deleted_at=NOW,
                ),
                _item(OTHER_ID, OTHER_USER_ID, NOW, Decimal("120")),
            ]
        )
        session.flush()
        session.add(
            CareNutrientSnapshot(
                id=SNAPSHOT_ID,
                care_item_id=LATEST_ID,
                nutrient_id=NUTRIENT_ID,
                nutrient_name="복용 관리 인수 성분",
                amount_per_unit=Decimal("10"),
                unit="MG",
            )
        )


def _item(
    item_id: UUID,
    user_id: UUID,
    created_at: datetime,
    quantity: Decimal,
    *,
    deleted_at: datetime | None = None,
) -> CareItem:
    return CareItem(
        id=item_id,
        user_id=user_id,
        product_id=PRODUCT_ID,
        purchase_date=date(2026, 8, 10),
        intake_start_date=date(2026, 8, 13),
        expected_depletion_date=date(2026, 9, 11),
        total_quantity=quantity,
        quantity_unit="PACKET",
        dose_per_intake=Decimal("1"),
        intakes_per_day=2,
        created_at=created_at,
        updated_at=deleted_at or created_at,
        deleted_at=deleted_at,
    )


def test_user_lists_independent_active_purchases_and_soft_deletes_one() -> None:
    with TestClient(app) as client:
        first_page = client.get(
            "/api/v1/care/items",
            params={"page": 1, "page_size": 1},
        )
        second_page = client.get(
            "/api/v1/care/items",
            params={"page": 2, "page_size": 1},
        )
        deleted = client.delete(f"/api/v1/care/items/{LATEST_ID}")
        after_delete = client.get("/api/v1/care/items")

    assert first_page.status_code == second_page.status_code == 200
    assert first_page.json()["total"] == second_page.json()["total"] == 2
    assert first_page.json()["has_next"] is True
    assert [item["id"] for item in first_page.json()["items"]] == [str(LATEST_ID)]
    assert [item["id"] for item in second_page.json()["items"]] == [str(FIRST_ID)]
    assert first_page.json()["items"][0]["name"] == "복용 관리 비게시 제품"
    assert first_page.json()["items"][0]["total_quantity"] == "60"
    assert first_page.json()["items"][0]["quantity_unit"] == "PACKET"
    assert first_page.json()["items"][0]["expected_depletion_date"] == "2026-09-11"
    assert first_page.json()["items"][0]["days_until_depletion"] == 29

    assert deleted.status_code == 204
    assert deleted.headers["cache-control"] == "no-store"
    assert after_delete.json()["total"] == 1
    assert [item["id"] for item in after_delete.json()["items"]] == [str(FIRST_ID)]

    with SessionFactory() as session:
        stored = session.get(CareItem, LATEST_ID)
        snapshot_count = session.scalar(
            select(func.count())
            .select_from(CareNutrientSnapshot)
            .where(CareNutrientSnapshot.care_item_id == LATEST_ID)
        )
    assert stored is not None
    assert stored.deleted_at == NOW
    assert snapshot_count == 1


@pytest.mark.parametrize("item_id", [OTHER_ID, DELETED_ID, MISSING_ID])
def test_delete_hides_other_missing_and_already_deleted_items(item_id: UUID) -> None:
    with TestClient(app) as client:
        response = client.delete(f"/api/v1/care/items/{item_id}")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "CARE_ITEM_NOT_FOUND",
        "message": "복용 항목을 찾을 수 없습니다.",
        "fields": [],
        "request_id": response.json()["error"]["request_id"],
    }
