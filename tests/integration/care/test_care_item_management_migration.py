from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, inspect, text

from yeongyangkkuk.auth.models import User
from yeongyangkkuk.care.models import CareItem
from yeongyangkkuk.curation.models import Nutrient, Product
from yeongyangkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.4")]

NOW = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000218")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000218")
NUTRIENT_ID = UUID("23000000-0000-4000-8000-000000000218")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000220")
SNAPSHOT_ID = UUID("32000000-0000-4000-8000-000000000218")


def test_0014_adds_soft_delete_without_losing_existing_history() -> None:
    config = Config("alembic.ini")
    _clean_at_head()
    command.downgrade(config, "20260812_0013")
    try:
        _seed_at_0013()
        command.upgrade(config, "head")

        columns = {
            column["name"]: column
            for column in inspect(engine).get_columns("care_items")
        }
        indexes = {item["name"] for item in inspect(engine).get_indexes("care_items")}
        with SessionFactory() as session:
            deleted_at = session.scalar(
                text("SELECT deleted_at FROM care_items WHERE id = :id"),
                {"id": ITEM_ID},
            )
        assert columns["deleted_at"]["nullable"] is True
        assert "ix_care_items_active_user_created_at" in indexes
        assert deleted_at is None

        with SessionFactory.begin() as session:
            session.execute(
                text(
                    "UPDATE care_items SET deleted_at = :now, updated_at = :now "
                    "WHERE id = :id"
                ),
                {"now": NOW, "id": ITEM_ID},
            )
        command.downgrade(config, "20260812_0013")

        names = {item["name"] for item in inspect(engine).get_columns("care_items")}
        with SessionFactory() as session:
            item_count = session.scalar(
                text("SELECT count(*) FROM care_items WHERE id = :id"),
                {"id": ITEM_ID},
            )
            snapshot_count = session.scalar(
                text("SELECT count(*) FROM care_nutrient_snapshots WHERE id = :id"),
                {"id": SNAPSHOT_ID},
            )
        assert "deleted_at" not in names
        assert item_count == snapshot_count == 1
    finally:
        command.upgrade(config, "head")
        _clean_at_head()


def _seed_at_0013() -> None:
    with SessionFactory.begin() as session:
        session.execute(
            text(
                """
                INSERT INTO users (
                    id, name, login_id, normalized_login_id, email,
                    normalized_email, password_hash, email_verified_at,
                    status, created_at, updated_at
                ) VALUES (
                    :id, '소프트 삭제 백필 사용자', 'SoftDelete218',
                    'softdelete218', 'soft-delete-218@example.com',
                    'soft-delete-218@example.com', 'not-a-real-password-hash',
                    :now, 'ACTIVE', :now, :now
                )
                """
            ),
            {"id": USER_ID, "now": NOW},
        )
        session.execute(
            text(
                """
                INSERT INTO products (
                    id, sku, product_type, brand, name, image_url, unit_form,
                    units_per_package, display_price, is_published, sort_order,
                    created_at, updated_at
                ) VALUES (
                    :id, 'SOFT-DELETE-218', 'SUPPLEMENT', '백필 브랜드',
                    '백필 제품', '/static/products/soft-delete-218.svg',
                    'CAPSULE', 30, 0, false, 218, :now, :now
                )
                """
            ),
            {"id": PRODUCT_ID, "now": NOW},
        )
        session.execute(
            text(
                """
                INSERT INTO nutrients (
                    id, code, name, canonical_unit, is_active
                ) VALUES (
                    :id, 'SOFT_DELETE_218', '백필 성분', 'MG', true
                )
                """
            ),
            {"id": NUTRIENT_ID},
        )
        session.execute(
            text(
                """
                INSERT INTO care_items (
                    id, user_id, product_id, purchase_date, intake_start_date,
                    total_quantity, quantity_unit, dose_per_intake,
                    intakes_per_day, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :product_id, DATE '2026-08-10',
                    DATE '2026-08-13', 30, 'CAPSULE', 1, 2, :now, :now
                )
                """
            ),
            {
                "id": ITEM_ID,
                "user_id": USER_ID,
                "product_id": PRODUCT_ID,
                "now": NOW,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO care_nutrient_snapshots (
                    id, care_item_id, nutrient_id, nutrient_name,
                    amount_per_unit, unit
                ) VALUES (
                    :id, :item_id, :nutrient_id, '백필 성분', 5, 'MG'
                )
                """
            ),
            {
                "id": SNAPSHOT_ID,
                "item_id": ITEM_ID,
                "nutrient_id": NUTRIENT_ID,
            },
        )


def _clean_at_head() -> None:
    with SessionFactory.begin() as session:
        session.execute(delete(CareItem).where(CareItem.user_id == USER_ID))
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(Nutrient).where(Nutrient.id == NUTRIENT_ID))
        session.execute(delete(User).where(User.id == USER_ID))
