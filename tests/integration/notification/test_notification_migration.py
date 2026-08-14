from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from allyakkkuk.auth.models import User, UserStatus
from allyakkkuk.curation.models import Product
from allyakkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.8")]

NOW = datetime(2026, 8, 14, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000381")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000381")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000381")


def test_0019_creates_notification_contract_and_preserves_care_on_downgrade() -> None:
    config = Config("alembic.ini")
    _clean_at_head()
    command.downgrade(config, "20260814_0018")
    try:
        _seed_at_0018()
        command.upgrade(config, "head")

        inspector = inspect(engine)
        columns = {
            column["name"]: column for column in inspector.get_columns("notifications")
        }
        checks = {
            check["name"] for check in inspector.get_check_constraints("notifications")
        }
        foreign_keys = {
            key["name"]: key for key in inspector.get_foreign_keys("notifications")
        }
        unique_constraints = {
            constraint["name"]: tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("notifications")
        }
        indexes = {
            index["name"]: index for index in inspector.get_indexes("notifications")
        }

        assert set(columns) == {
            "id",
            "user_id",
            "care_item_id",
            "notification_type",
            "reference_date",
            "trigger_days_before",
            "scheduled_at",
            "created_at",
            "read_at",
        }
        assert columns["read_at"]["nullable"] is True
        assert all(
            not column["nullable"]
            for name, column in columns.items()
            if name != "read_at"
        )
        assert checks >= {
            "ck_notifications_type",
            "ck_notifications_trigger_days",
            "ck_notifications_scheduled_at",
            "ck_notifications_read_at",
        }
        assert (
            foreign_keys["fk_notifications_user_id_users"]["options"]["ondelete"]
            == "CASCADE"
        )
        assert (
            foreign_keys["fk_notifications_care_item_id_care_items"]["options"][
                "ondelete"
            ]
            == "CASCADE"
        )
        assert unique_constraints["uq_notifications_logical_event"] == (
            "care_item_id",
            "notification_type",
            "reference_date",
            "trigger_days_before",
        )
        notification_index = indexes["ix_notifications_user_read_created"]
        assert tuple(notification_index["column_names"]) == (
            "user_id",
            "read_at",
            "created_at",
            "id",
        )
        assert notification_index["column_sorting"]["created_at"] == ("desc",)

        command.downgrade(config, "20260814_0018")
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


def _seed_at_0018() -> None:
    with SessionFactory.begin() as session:
        session.add(
            User(
                id=USER_ID,
                name="알림 마이그레이션 사용자",
                login_id="Notification381",
                normalized_login_id="notification381",
                email="notification-381@example.com",
                normalized_email="notification-381@example.com",
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
                sku="NOTIFICATION-381",
                product_type="SUPPLEMENT",
                brand="알림 마이그레이션",
                name="알림 마이그레이션 제품",
                image_url="/static/products/notification-381.svg",
                unit_form="CAPSULE",
                units_per_package=Decimal("30"),
                display_price=0,
                is_published=False,
                sort_order=381,
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
                    expected_depletion_date, expiration_date, total_quantity,
                    quantity_unit, dose_per_intake, intakes_per_day,
                    created_at, updated_at, deleted_at
                ) VALUES (
                    :id, :user_id, :product_id, DATE '2026-08-01',
                    DATE '2026-08-01', DATE '2026-08-19', NULL, 30,
                    'CAPSULE', 1, 1, :now, :now, NULL
                )
                """
            ),
            {"id": ITEM_ID, "user_id": USER_ID, "product_id": PRODUCT_ID, "now": NOW},
        )


def _clean_at_head() -> None:
    with SessionFactory.begin() as session:
        session.execute(
            text("DELETE FROM notifications WHERE user_id = :id"), {"id": USER_ID}
        )
        session.execute(text("DELETE FROM care_items WHERE id = :id"), {"id": ITEM_ID})
        session.execute(text("DELETE FROM products WHERE id = :id"), {"id": PRODUCT_ID})
        session.execute(text("DELETE FROM users WHERE id = :id"), {"id": USER_ID})
