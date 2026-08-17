from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import delete, select, update

from yeongyangkkuk.auth.models import User, UserStatus
from yeongyangkkuk.care.care_item_repository import (
    CareItemCreateData,
    SQLAlchemyCareItemRepository,
)
from yeongyangkkuk.care.models import CareItem, CareNutrientSnapshot
from yeongyangkkuk.curation.models import Nutrient, Product, ProductNutrient
from yeongyangkkuk.db.session import SessionFactory

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.3")]

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000208")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000208")
NUTRIENT_ID = UUID("23000000-0000-4000-8000-000000000208")


@pytest.fixture(autouse=True)
def clean_data() -> Iterator[None]:
    _clean_data()
    yield
    _clean_data()


def _clean_data() -> None:
    with SessionFactory.begin() as session:
        session.execute(delete(CareItem).where(CareItem.user_id == USER_ID))
        session.execute(
            delete(ProductNutrient).where(ProductNutrient.product_id == PRODUCT_ID)
        )
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(Nutrient).where(Nutrient.id == NUTRIENT_ID))
        session.execute(delete(User).where(User.id == USER_ID))


def _seed_catalog() -> None:
    with SessionFactory.begin() as session:
        session.add(
            User(
                id=USER_ID,
                name="구매 이력 사용자",
                login_id="Inventory208",
                normalized_login_id="inventory208",
                email="inventory-208@example.com",
                normalized_email="inventory-208@example.com",
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
                sku="INVENTORY-208",
                product_type="SUPPLEMENT",
                brand="구매 이력 브랜드",
                name="구매 이력 영양제",
                image_url="/static/products/inventory-208.svg",
                unit_form="PACKET",
                units_per_package=Decimal("30"),
                display_price=10000,
                is_published=False,
                sort_order=208,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.add(
            Nutrient(
                id=NUTRIENT_ID,
                code="INVENTORY_NUTRIENT_208",
                name="구매 이력 성분",
                canonical_unit="MG",
                is_active=True,
            )
        )
        session.flush()
        session.add(
            ProductNutrient(
                product_id=PRODUCT_ID,
                nutrient_id=NUTRIENT_ID,
                amount_per_unit=Decimal("15.0000"),
                unit="MG",
                sort_order=1,
            )
        )


def _create_data(total_quantity: Decimal) -> CareItemCreateData:
    return CareItemCreateData(
        user_id=USER_ID,
        product_id=PRODUCT_ID,
        purchase_date=date(2026, 8, 10),
        intake_start_date=date(2026, 8, 12),
        expected_depletion_date=date(2026, 8, 26),
        total_quantity=total_quantity,
        dose_per_intake=Decimal("1"),
        intakes_per_day=2,
        created_at=NOW,
    )


def test_repurchase_keeps_independent_quantity_and_catalog_unit_snapshots() -> None:
    _seed_catalog()
    with SessionFactory() as session:
        first = SQLAlchemyCareItemRepository(session).create(
            _create_data(Decimal("30"))
        )
    assert first is not None

    with SessionFactory.begin() as session:
        session.execute(
            update(Product).where(Product.id == PRODUCT_ID).values(unit_form="CAPSULE")
        )

    with SessionFactory() as session:
        second = SQLAlchemyCareItemRepository(session).create(
            _create_data(Decimal("60"))
        )
    assert second is not None

    with SessionFactory() as session:
        items = {
            item.id: item
            for item in session.scalars(
                select(CareItem).where(CareItem.user_id == USER_ID)
            )
        }
        snapshot_item_ids = set(
            session.scalars(
                select(CareNutrientSnapshot.care_item_id).where(
                    CareNutrientSnapshot.nutrient_id == NUTRIENT_ID
                )
            )
        )

    assert first.id != second.id
    assert items[first.id].total_quantity == Decimal("30")
    assert items[first.id].quantity_unit == "PACKET"
    assert items[second.id].total_quantity == Decimal("60")
    assert items[second.id].quantity_unit == "CAPSULE"
    assert snapshot_item_ids == {first.id, second.id}
