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

from yeongyangkkuk.auth.current_user_dependencies import require_current_user
from yeongyangkkuk.auth.current_user_service import AuthenticatedUser
from yeongyangkkuk.auth.models import Gender, User, UserStatus
from yeongyangkkuk.care.care_item_repository import SQLAlchemyCareItemRepository
from yeongyangkkuk.care.care_item_router import get_care_item_service
from yeongyangkkuk.care.care_item_service import CareItemService
from yeongyangkkuk.care.models import CareItem, CareNutrientSnapshot
from yeongyangkkuk.curation.models import Nutrient, Product, ProductNutrient
from yeongyangkkuk.db.session import SessionFactory, get_db_session
from yeongyangkkuk.main import app
from yeongyangkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.2")]

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000205")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000205")
NUTRIENT_ID = UUID("23000000-0000-4000-8000-000000000205")


def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=USER_ID,
        login_id="Snapshot205",
        name="스냅샷 인수 사용자",
        email="snapshot-205@example.com",
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
def snapshot_environment() -> Iterator[None]:
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
                name="스냅샷 인수 사용자",
                login_id="Snapshot205",
                normalized_login_id="snapshot205",
                email="snapshot-205@example.com",
                normalized_email="snapshot-205@example.com",
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
                sku="SNAPSHOT-ACCEPT-205",
                product_type="SUPPLEMENT",
                brand="스냅샷 인수 브랜드",
                name="스냅샷 인수 영양제",
                image_url="/static/products/snapshot-accept-205.svg",
                unit_form="CAPSULE",
                units_per_package=Decimal("60"),
                display_price=10000,
                is_published=False,
                sort_order=205,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.add(
            Nutrient(
                id=NUTRIENT_ID,
                code="SNAPSHOT_ACCEPT_205",
                name="등록 당시 비타민",
                canonical_unit="MG",
                is_active=True,
            )
        )
        session.flush()
        session.add(
            ProductNutrient(
                product_id=PRODUCT_ID,
                nutrient_id=NUTRIENT_ID,
                amount_per_unit=Decimal("25.5000"),
                unit="MG",
                sort_order=1,
            )
        )
    yield
    app.dependency_overrides.pop(require_current_user, None)
    app.dependency_overrides.pop(get_care_item_service, None)
    _clean_data()


def _clean_data() -> None:
    with SessionFactory.begin() as session:
        session.execute(
            delete(CareNutrientSnapshot).where(
                CareNutrientSnapshot.nutrient_id == NUTRIENT_ID
            )
        )
        session.execute(delete(CareItem).where(CareItem.user_id == USER_ID))
        session.execute(
            delete(ProductNutrient).where(ProductNutrient.product_id == PRODUCT_ID)
        )
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(Nutrient).where(Nutrient.id == NUTRIENT_ID))
        session.execute(delete(User).where(User.id == USER_ID))


def test_registration_freezes_nutrient_values_without_changing_http_response() -> None:
    payload = {
        "product_id": str(PRODUCT_ID),
        "purchase_date": "2026-08-10",
        "intake_start_date": "2026-08-12",
        "total_quantity": "60",
        "dose_per_intake": "1",
        "intakes_per_day": 2,
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/care/items", json=payload)

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert "nutrient_snapshots" not in response.json()
    item_id = UUID(response.json()["id"])
    with SessionFactory() as session:
        original = session.scalar(
            select(CareNutrientSnapshot).where(
                CareNutrientSnapshot.care_item_id == item_id
            )
        )
    assert original is not None
    assert original.nutrient_name == "등록 당시 비타민"
    assert original.amount_per_unit == Decimal("25.5000")
    assert original.unit == "MG"

    with SessionFactory.begin() as session:
        session.execute(
            update(ProductNutrient)
            .where(ProductNutrient.product_id == PRODUCT_ID)
            .values(amount_per_unit=Decimal("0.7500"), unit="G")
        )
        session.execute(
            update(Nutrient)
            .where(Nutrient.id == NUTRIENT_ID)
            .values(name="카탈로그 변경 이름", is_active=False)
        )

    with SessionFactory() as session:
        unchanged = session.scalar(
            select(CareNutrientSnapshot).where(
                CareNutrientSnapshot.care_item_id == item_id
            )
        )
    assert unchanged is not None
    assert unchanged.nutrient_name == "등록 당시 비타민"
    assert unchanged.amount_per_unit == Decimal("25.5000")
    assert unchanged.unit == "MG"
