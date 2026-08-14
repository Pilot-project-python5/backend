from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from allyakkkuk.auth.models import User, UserStatus
from allyakkkuk.care.models import CareItem
from allyakkkuk.curation.models import Product
from allyakkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.11")]

NOW = datetime(2026, 8, 14, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000311")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000311")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000311")


def test_0018_keeps_existing_item_nullable_and_preserves_it_on_downgrade() -> None:
    config = Config("alembic.ini")
    _clean_at_head()
    command.downgrade(config, "20260814_0017")
    try:
        _seed_at_0017()
        command.upgrade(config, "head")

        columns = {
            column["name"]: column
            for column in inspect(engine).get_columns("care_items")
        }
        indexes = {
            index["name"]: tuple(index["column_names"])
            for index in inspect(engine).get_indexes("care_items")
        }
        with SessionFactory() as session:
            item = session.get(CareItem, ITEM_ID)

        assert item is not None
        assert item.expiration_date is None
        assert columns["expiration_date"]["nullable"] is True
        assert indexes["ix_care_items_expiration_user"] == (
            "expiration_date",
            "user_id",
        )

        command.downgrade(config, "20260814_0017")
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


def _seed_at_0017() -> None:
    with SessionFactory.begin() as session:
        session.add(
            User(
                id=USER_ID,
                name="유통기한 마이그레이션 사용자",
                login_id="Expiration311",
                normalized_login_id="expiration311",
                email="expiration-311@example.com",
                normalized_email="expiration-311@example.com",
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
                sku="EXPIRATION-311",
                product_type="MEDICATION",
                brand="유통기한 테스트",
                name="유통기한 테스트 제품",
                image_url="/static/products/expiration-311.svg",
                unit_form="TABLET",
                units_per_package=Decimal("30"),
                display_price=0,
                is_published=False,
                sort_order=311,
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
                    expected_depletion_date, total_quantity, quantity_unit,
                    dose_per_intake, intakes_per_day, created_at, updated_at,
                    deleted_at
                ) VALUES (
                    :id, :user_id, :product_id, DATE '2026-08-01',
                    DATE '2026-08-01', DATE '2026-08-30', 30, 'TABLET', 1, 1,
                    :now, :now, NULL
                )
                """
            ),
            {"id": ITEM_ID, "user_id": USER_ID, "product_id": PRODUCT_ID, "now": NOW},
        )


def _clean_at_head() -> None:
    with SessionFactory.begin() as session:
        session.execute(text("DELETE FROM care_items WHERE id = :id"), {"id": ITEM_ID})
        session.execute(text("DELETE FROM products WHERE id = :id"), {"id": PRODUCT_ID})
        session.execute(text("DELETE FROM users WHERE id = :id"), {"id": USER_ID})
