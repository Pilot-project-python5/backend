from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, inspect, select, text

from allyakkkuk.auth.models import User, UserStatus
from allyakkkuk.care.models import CareItem, CareNutrientSnapshot
from allyakkkuk.curation.models import Nutrient, Product, ProductNutrient
from allyakkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.2")]

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000206")
SUPPLEMENT_ID = UUID("22000000-0000-4000-8000-000000000206")
MEDICATION_ID = UUID("22000000-0000-4000-8000-000000000207")
ACTIVE_NUTRIENT_ID = UUID("23000000-0000-4000-8000-000000000206")
INACTIVE_NUTRIENT_ID = UUID("23000000-0000-4000-8000-000000000207")
SUPPLEMENT_ITEM_ID = UUID("31000000-0000-4000-8000-000000000206")
MEDICATION_ITEM_ID = UUID("31000000-0000-4000-8000-000000000207")


def test_0012_backfills_existing_supplement_and_preserves_items_on_downgrade() -> None:
    config = Config("alembic.ini")
    _clean_at_head()
    command.downgrade(config, "20260812_0011")
    try:
        _seed_at_0011()
        command.upgrade(config, "head")

        with SessionFactory() as session:
            snapshots = tuple(
                session.scalars(
                    select(CareNutrientSnapshot).order_by(
                        CareNutrientSnapshot.care_item_id,
                        CareNutrientSnapshot.nutrient_id,
                    )
                )
            )
        assert len(snapshots) == 1
        assert snapshots[0].care_item_id == SUPPLEMENT_ITEM_ID
        assert snapshots[0].nutrient_id == ACTIVE_NUTRIENT_ID
        assert snapshots[0].nutrient_name == "백필 활성 성분"
        assert snapshots[0].amount_per_unit == Decimal("12.5000")

        command.downgrade(config, "20260812_0011")
        assert "care_nutrient_snapshots" not in inspect(engine).get_table_names()
        with SessionFactory() as session:
            item_ids = set(session.scalars(select(CareItem.id)))
        assert item_ids >= {SUPPLEMENT_ITEM_ID, MEDICATION_ITEM_ID}
    finally:
        command.upgrade(config, "head")
        _clean_at_head()


def _product(product_id: UUID, product_type: str) -> Product:
    suffix = str(product_id)[-3:]
    return Product(
        id=product_id,
        sku=f"BACKFILL-{suffix}",
        product_type=product_type,
        brand="백필 테스트",
        name=f"백필 제품 {suffix}",
        image_url=f"/static/products/backfill-{suffix}.svg",
        unit_form="TABLET",
        units_per_package=Decimal("30"),
        display_price=0,
        is_published=False,
        sort_order=206,
        created_at=NOW,
        updated_at=NOW,
    )


def _seed_at_0011() -> None:
    with SessionFactory.begin() as session:
        session.add(
            User(
                id=USER_ID,
                name="백필 사용자",
                login_id="Backfill206",
                normalized_login_id="backfill206",
                email="backfill-206@example.com",
                normalized_email="backfill-206@example.com",
                password_hash="not-a-real-password-hash",
                email_verified_at=NOW,
                status=UserStatus.ACTIVE.value,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.add_all(
            [
                _product(SUPPLEMENT_ID, "SUPPLEMENT"),
                _product(MEDICATION_ID, "MEDICATION"),
                Nutrient(
                    id=ACTIVE_NUTRIENT_ID,
                    code="BACKFILL_ACTIVE_206",
                    name="백필 활성 성분",
                    canonical_unit="MG",
                    is_active=True,
                ),
                Nutrient(
                    id=INACTIVE_NUTRIENT_ID,
                    code="BACKFILL_INACTIVE_207",
                    name="백필 비활성 성분",
                    canonical_unit="MG",
                    is_active=False,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                ProductNutrient(
                    product_id=SUPPLEMENT_ID,
                    nutrient_id=ACTIVE_NUTRIENT_ID,
                    amount_per_unit=Decimal("12.5000"),
                    unit="MG",
                    sort_order=1,
                ),
                ProductNutrient(
                    product_id=SUPPLEMENT_ID,
                    nutrient_id=INACTIVE_NUTRIENT_ID,
                    amount_per_unit=Decimal("4.0000"),
                    unit="MG",
                    sort_order=2,
                ),
                ProductNutrient(
                    product_id=MEDICATION_ID,
                    nutrient_id=ACTIVE_NUTRIENT_ID,
                    amount_per_unit=Decimal("99.0000"),
                    unit="MG",
                    sort_order=1,
                ),
            ]
        )
        session.flush()
        for item_id, product_id in (
            (SUPPLEMENT_ITEM_ID, SUPPLEMENT_ID),
            (MEDICATION_ITEM_ID, MEDICATION_ID),
        ):
            session.execute(
                text(
                    """
                    INSERT INTO care_items (
                        id, user_id, product_id, purchase_date,
                        intake_start_date, total_quantity, dose_per_intake,
                        intakes_per_day, created_at, updated_at
                    ) VALUES (
                        :id, :user_id, :product_id, DATE '2026-08-10',
                        DATE '2026-08-12', 30, 1, 1, :created_at, :updated_at
                    )
                    """
                ),
                {
                    "id": item_id,
                    "user_id": USER_ID,
                    "product_id": product_id,
                    "created_at": NOW,
                    "updated_at": NOW,
                },
            )


def _clean_at_head() -> None:
    product_ids = (SUPPLEMENT_ID, MEDICATION_ID)
    nutrient_ids = (ACTIVE_NUTRIENT_ID, INACTIVE_NUTRIENT_ID)
    with SessionFactory.begin() as session:
        session.execute(
            delete(CareNutrientSnapshot).where(
                CareNutrientSnapshot.nutrient_id.in_(nutrient_ids)
            )
        )
        session.execute(delete(CareItem).where(CareItem.user_id == USER_ID))
        session.execute(
            delete(ProductNutrient).where(ProductNutrient.product_id.in_(product_ids))
        )
        session.execute(delete(Product).where(Product.id.in_(product_ids)))
        session.execute(delete(Nutrient).where(Nutrient.id.in_(nutrient_ids)))
        session.execute(delete(User).where(User.id == USER_ID))
