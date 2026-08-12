from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, inspect, text

from allyakkkuk.auth.models import User, UserStatus
from allyakkkuk.care.models import CareItem
from allyakkkuk.curation.models import Nutrient, Product
from allyakkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.3")]

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000210")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000210")
NUTRIENT_ID = UUID("23000000-0000-4000-8000-000000000210")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000210")
SNAPSHOT_ID = UUID("32000000-0000-4000-8000-000000000210")


def test_0013_backfills_quantity_unit_and_preserves_history_on_downgrade() -> None:
    config = Config("alembic.ini")
    _clean_at_head()
    command.downgrade(config, "20260812_0012")
    try:
        _seed_at_0012()
        command.upgrade(config, "head")

        with SessionFactory() as session:
            item = session.get(CareItem, ITEM_ID)
        assert item is not None
        assert item.quantity_unit == "SCOOP"

        command.downgrade(config, "20260812_0012")
        columns = {
            column["name"] for column in inspect(engine).get_columns("care_items")
        }
        assert "quantity_unit" not in columns
        with SessionFactory() as session:
            item_count = session.scalar(
                text("SELECT count(*) FROM care_items WHERE id = :id"),
                {"id": ITEM_ID},
            )
            snapshot_count = session.scalar(
                text("SELECT count(*) FROM care_nutrient_snapshots WHERE id = :id"),
                {"id": SNAPSHOT_ID},
            )
        assert item_count == 1
        assert snapshot_count == 1
    finally:
        command.upgrade(config, "head")
        _clean_at_head()


def _seed_at_0012() -> None:
    with SessionFactory.begin() as session:
        session.add(
            User(
                id=USER_ID,
                name="수량 백필 사용자",
                login_id="InventoryBackfill210",
                normalized_login_id="inventorybackfill210",
                email="inventory-backfill-210@example.com",
                normalized_email="inventory-backfill-210@example.com",
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
                sku="INVENTORY-BACKFILL-210",
                product_type="SUPPLEMENT",
                brand="수량 백필 브랜드",
                name="수량 백필 제품",
                image_url="/static/products/inventory-backfill-210.svg",
                unit_form="SCOOP",
                units_per_package=Decimal("30"),
                display_price=0,
                is_published=False,
                sort_order=210,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.add(
            Nutrient(
                id=NUTRIENT_ID,
                code="INVENTORY_BACKFILL_210",
                name="수량 백필 성분",
                canonical_unit="MG",
                is_active=True,
            )
        )
        session.flush()
        session.execute(
            text(
                """
                INSERT INTO care_items (
                    id, user_id, product_id, purchase_date, intake_start_date,
                    total_quantity, dose_per_intake, intakes_per_day,
                    created_at, updated_at
                ) VALUES (
                    :id, :user_id, :product_id, DATE '2026-08-10',
                    DATE '2026-08-12', 30, 1, 2, :created_at, :updated_at
                )
                """
            ),
            {
                "id": ITEM_ID,
                "user_id": USER_ID,
                "product_id": PRODUCT_ID,
                "created_at": NOW,
                "updated_at": NOW,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO care_nutrient_snapshots (
                    id, care_item_id, nutrient_id, nutrient_name,
                    amount_per_unit, unit
                ) VALUES (
                    :id, :care_item_id, :nutrient_id,
                    '수량 백필 성분', 5, 'MG'
                )
                """
            ),
            {
                "id": SNAPSHOT_ID,
                "care_item_id": ITEM_ID,
                "nutrient_id": NUTRIENT_ID,
            },
        )


def _clean_at_head() -> None:
    with SessionFactory.begin() as session:
        session.execute(delete(CareItem).where(CareItem.user_id == USER_ID))
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(Nutrient).where(Nutrient.id == NUTRIENT_ID))
        session.execute(delete(User).where(User.id == USER_ID))
