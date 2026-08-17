from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, inspect, text

from yeongyangkkuk.auth.models import User, UserStatus
from yeongyangkkuk.care.models import CareItem
from yeongyangkkuk.curation.models import Product
from yeongyangkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.7")]

NOW = datetime(2026, 8, 14, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000370")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000370")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000370")


def test_0016_backfills_partial_final_day_and_preserves_item_on_downgrade() -> None:
    config = Config("alembic.ini")
    _clean_at_head()
    command.downgrade(config, "20260814_0015")
    try:
        _seed_at_0015()
        command.upgrade(config, "head")

        with SessionFactory() as session:
            item = session.get(CareItem, ITEM_ID)
            assert item is not None
            assert item.expected_depletion_date == date(2026, 8, 4)

        columns = {
            column["name"]: column
            for column in inspect(engine).get_columns("care_items")
        }
        assert columns["expected_depletion_date"]["nullable"] is False
        assert "ix_care_items_depletion_user" in {
            index["name"] for index in inspect(engine).get_indexes("care_items")
        }

        command.downgrade(config, "20260814_0015")
        with engine.connect() as connection:
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM care_items WHERE id = :id"),
                    {"id": ITEM_ID},
                )
                == 1
            )
    finally:
        command.upgrade(config, "head")
        _clean_at_head()


def _seed_at_0015() -> None:
    with SessionFactory.begin() as session:
        session.add(
            User(
                id=USER_ID,
                name="소진일 백필 사용자",
                login_id="Depletion370",
                normalized_login_id="depletion370",
                email="depletion-370@example.com",
                normalized_email="depletion-370@example.com",
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
                sku="DEPLETION-370",
                product_type="SUPPLEMENT",
                brand="소진일 테스트",
                name="소진일 테스트 제품",
                image_url="/static/products/depletion-370.svg",
                unit_form="TABLET",
                units_per_package=Decimal("10"),
                display_price=0,
                is_published=False,
                sort_order=370,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.flush()
        session.execute(
            text(
                """
                INSERT INTO care_items (
                    id, user_id, product_id, purchase_date, intake_start_date,
                    total_quantity, quantity_unit, dose_per_intake,
                    intakes_per_day, created_at, updated_at, deleted_at
                ) VALUES (
                    :id, :user_id, :product_id, DATE '2026-08-01', DATE '2026-08-01',
                    10, 'TABLET', 1, 3, :now, :now, NULL
                )
                """
            ),
            {"id": ITEM_ID, "user_id": USER_ID, "product_id": PRODUCT_ID, "now": NOW},
        )


def _clean_at_head() -> None:
    with SessionFactory.begin() as session:
        session.execute(delete(CareItem).where(CareItem.id == ITEM_ID))
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(User).where(User.id == USER_ID))
