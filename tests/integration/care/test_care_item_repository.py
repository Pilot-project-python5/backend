from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import delete, func, inspect, select

from yeongyangkkuk.auth.models import User, UserStatus
from yeongyangkkuk.care.care_item_repository import (
    CareItemCreateData,
    SQLAlchemyCareItemRepository,
)
from yeongyangkkuk.care.models import CareItem
from yeongyangkkuk.curation.models import Product
from yeongyangkkuk.db.session import SessionFactory, engine

pytestmark = [
    pytest.mark.integration,
    pytest.mark.feature("F-3.1"),
    pytest.mark.feature("F-3.11"),
]

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000032")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000032")


@pytest.fixture(autouse=True)
def clean_data() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(CareItem))
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(User).where(User.id == USER_ID))
    yield
    with SessionFactory.begin() as session:
        session.execute(delete(CareItem))
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(User).where(User.id == USER_ID))


def add_catalog_and_user() -> None:
    with SessionFactory.begin() as session:
        session.add(
            User(
                id=USER_ID,
                name="복용 저장 사용자",
                login_id="CareRepo32",
                normalized_login_id="carerepo32",
                email="care-repo32@example.com",
                normalized_email="care-repo32@example.com",
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
                sku="CARE-REPO-32",
                product_type="MEDICATION",
                brand="복용 테스트",
                name="게시되지 않은 의약품",
                image_url="/static/products/care-repo-32.svg",
                unit_form="TABLET",
                units_per_package=Decimal("30"),
                display_price=0,
                is_published=False,
                sort_order=32,
                created_at=NOW,
                updated_at=NOW,
            )
        )


def create_data(product_id: UUID = PRODUCT_ID) -> CareItemCreateData:
    return CareItemCreateData(
        user_id=USER_ID,
        product_id=product_id,
        purchase_date=date(2026, 8, 10),
        intake_start_date=date(2026, 8, 12),
        expected_depletion_date=date(2026, 8, 21),
        total_quantity=Decimal("30"),
        dose_per_intake=Decimal("1"),
        intakes_per_day=3,
        created_at=NOW,
        expiration_date=date(2027, 1, 31),
    )


def test_repository_registers_unpublished_catalog_item_as_distinct_history() -> None:
    add_catalog_and_user()

    with SessionFactory() as session:
        repository = SQLAlchemyCareItemRepository(session)
        first = repository.create(create_data())
        second = repository.create(create_data())

    assert first is not None
    assert second is not None
    assert first.id != second.id
    assert first.user_id == second.user_id == USER_ID
    assert first.quantity_unit == second.quantity_unit == "TABLET"
    assert first.expiration_date == second.expiration_date == date(2027, 1, 31)
    with SessionFactory() as session:
        count = session.scalar(
            select(func.count())
            .select_from(CareItem)
            .where(CareItem.user_id == USER_ID)
        )
    assert count == 2


def test_repository_rejects_product_outside_database_catalog_without_write() -> None:
    add_catalog_and_user()
    missing_id = UUID("22000000-0000-4000-8000-000000000099")

    with SessionFactory() as session:
        result = SQLAlchemyCareItemRepository(session).create(
            create_data(product_id=missing_id)
        )

    assert result is None
    with SessionFactory() as session:
        count = session.scalar(select(func.count()).select_from(CareItem))
    assert count == 0


@pytest.mark.feature("F-3.7")
@pytest.mark.feature("F-3.11")
def test_care_item_schema_matches_model_and_erd_contract() -> None:
    inspector = inspect(engine)
    columns = {item["name"]: item for item in inspector.get_columns("care_items")}
    checks = {item["name"] for item in inspector.get_check_constraints("care_items")}
    foreign_keys = {
        item["name"]: item for item in inspector.get_foreign_keys("care_items")
    }
    indexes = {
        item["name"]: tuple(item["column_names"])
        for item in inspector.get_indexes("care_items")
    }

    assert set(columns) == {
        "id",
        "user_id",
        "product_id",
        "purchase_date",
        "intake_start_date",
        "expected_depletion_date",
        "expiration_date",
        "total_quantity",
        "quantity_unit",
        "dose_per_intake",
        "intakes_per_day",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert columns["deleted_at"]["nullable"] is True
    assert columns["expiration_date"]["nullable"] is True
    assert all(
        not item["nullable"]
        for name, item in columns.items()
        if name not in {"deleted_at", "expiration_date"}
    )
    assert checks >= {
        "ck_care_items_date_order",
        "ck_care_items_depletion_date_order",
        "ck_care_items_total_quantity",
        "ck_care_items_quantity_unit",
        "ck_care_items_dose_per_intake",
        "ck_care_items_dose_within_total",
        "ck_care_items_intakes_per_day",
        "ck_care_items_updated_at",
        "ck_care_items_deleted_at",
    }
    assert foreign_keys["fk_care_items_user_id_users"]["options"]["ondelete"] == (
        "CASCADE"
    )
    assert foreign_keys["fk_care_items_product_id_products"]["options"]["ondelete"] == (
        "RESTRICT"
    )
    assert indexes["ix_care_items_user_created_at"] == (
        "user_id",
        "created_at",
        "id",
    )
    assert indexes["ix_care_items_product_id"] == ("product_id",)
    assert indexes["ix_care_items_depletion_user"] == (
        "expected_depletion_date",
        "user_id",
    )
    assert indexes["ix_care_items_expiration_user"] == (
        "expiration_date",
        "user_id",
    )
    assert indexes["ix_care_items_active_user_created_at"] == (
        "user_id",
        "created_at",
        "id",
    )
