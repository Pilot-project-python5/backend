from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from yeongyangkkuk.auth.models import User, UserStatus
from yeongyangkkuk.curation.models import Product
from yeongyangkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.12")]

NOW = datetime(2026, 8, 14, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000414")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000414")
ITEM_ID = UUID("31000000-0000-4000-8000-000000000414")
NOTIFICATION_ID = UUID("41000000-0000-4000-8000-000000000414")


def test_0020_creates_email_delivery_contract_and_preserves_notification() -> None:
    config = Config("alembic.ini")
    _clean_at_head()
    command.downgrade(config, "20260814_0019")
    try:
        _seed_at_0019()
        command.upgrade(config, "head")

        inspector = inspect(engine)
        columns = {
            column["name"]: column
            for column in inspector.get_columns("email_deliveries")
        }
        checks = {
            check["name"]
            for check in inspector.get_check_constraints("email_deliveries")
        }
        foreign_keys = {
            key["name"]: key for key in inspector.get_foreign_keys("email_deliveries")
        }
        unique_constraints = {
            constraint["name"]: tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("email_deliveries")
        }
        indexes = {
            index["name"]: index for index in inspector.get_indexes("email_deliveries")
        }

        assert set(columns) == {
            "id",
            "notification_id",
            "recipient_email",
            "status",
            "attempt_count",
            "next_retry_at",
            "sent_at",
            "last_error",
            "created_at",
            "updated_at",
        }
        assert checks >= {
            "ck_email_deliveries_status",
            "ck_email_deliveries_attempt_count",
            "ck_email_deliveries_last_error",
            "ck_email_deliveries_state",
            "ck_email_deliveries_sent_at",
            "ck_email_deliveries_updated_at",
        }
        assert (
            foreign_keys["fk_email_deliveries_notification_id_notifications"][
                "options"
            ]["ondelete"]
            == "CASCADE"
        )
        assert unique_constraints["uq_email_deliveries_notification_id"] == (
            "notification_id",
        )
        due_index = indexes["ix_email_deliveries_due"]
        assert tuple(due_index["column_names"]) == ("next_retry_at", "id")
        assert "status" in due_index["dialect_options"]["postgresql_where"]

        command.downgrade(config, "20260814_0019")
        with engine.connect() as connection:
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM notifications WHERE id = :id"),
                    {"id": NOTIFICATION_ID},
                )
                == 1
            )
    finally:
        command.upgrade(config, "head")
        _clean_at_head()


def _seed_at_0019() -> None:
    with SessionFactory.begin() as session:
        session.add(
            User(
                id=USER_ID,
                name="이메일 전달 마이그레이션 사용자",
                login_id="EmailMigration414",
                normalized_login_id="emailmigration414",
                email="email-migration-414@example.com",
                normalized_email="email-migration-414@example.com",
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
                sku="EMAIL-MIGRATION-414",
                product_type="SUPPLEMENT",
                brand="이메일 전달 마이그레이션",
                name="이메일 전달 마이그레이션 제품",
                image_url="/static/products/email-migration-414.svg",
                unit_form="CAPSULE",
                units_per_package=Decimal("30"),
                display_price=0,
                is_published=False,
                sort_order=414,
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
        session.execute(
            text(
                """
                INSERT INTO notifications (
                    id, user_id, care_item_id, notification_type, reference_date,
                    trigger_days_before, scheduled_at, created_at, read_at
                ) VALUES (
                    :id, :user_id, :care_item_id, 'REPURCHASE', DATE '2026-08-19',
                    5, :now, :now, NULL
                )
                """
            ),
            {
                "id": NOTIFICATION_ID,
                "user_id": USER_ID,
                "care_item_id": ITEM_ID,
                "now": NOW,
            },
        )


def _clean_at_head() -> None:
    with SessionFactory.begin() as session:
        session.execute(
            text("DELETE FROM email_deliveries WHERE notification_id = :id"),
            {"id": NOTIFICATION_ID},
        )
        session.execute(
            text("DELETE FROM notifications WHERE id = :id"),
            {"id": NOTIFICATION_ID},
        )
        session.execute(text("DELETE FROM care_items WHERE id = :id"), {"id": ITEM_ID})
        session.execute(text("DELETE FROM products WHERE id = :id"), {"id": PRODUCT_ID})
        session.execute(text("DELETE FROM users WHERE id = :id"), {"id": USER_ID})
