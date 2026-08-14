from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import delete, event, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.auth.models import User, UserStatus
from allyakkkuk.care.care_item_repository import (
    CareItemCreateData,
    CareItemPersistenceError,
    SQLAlchemyCareItemRepository,
)
from allyakkkuk.care.models import CareItem, CareNutrientSnapshot
from allyakkkuk.curation.models import Nutrient, Product, ProductNutrient
from allyakkkuk.db.session import SessionFactory

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.2")]

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000202")
SUPPLEMENT_ID = UUID("22000000-0000-4000-8000-000000000202")
MEDICATION_ID = UUID("22000000-0000-4000-8000-000000000203")
EMPTY_SUPPLEMENT_ID = UUID("22000000-0000-4000-8000-000000000204")
ACTIVE_NUTRIENT_ID = UUID("23000000-0000-4000-8000-000000000202")
INACTIVE_NUTRIENT_ID = UUID("23000000-0000-4000-8000-000000000203")


@pytest.fixture(autouse=True)
def clean_data() -> Iterator[None]:
    _clean_data()
    yield
    _clean_data()


def _clean_data() -> None:
    product_ids = (SUPPLEMENT_ID, MEDICATION_ID, EMPTY_SUPPLEMENT_ID)
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


def product(product_id: UUID, product_type: str) -> Product:
    suffix = str(product_id)[-3:]
    return Product(
        id=product_id,
        sku=f"SNAPSHOT-{suffix}",
        product_type=product_type,
        brand="스냅샷 테스트",
        name=f"스냅샷 제품 {suffix}",
        image_url=f"/static/products/snapshot-{suffix}.svg",
        unit_form="CAPSULE",
        units_per_package=Decimal("60"),
        display_price=10000,
        is_published=False,
        sort_order=202,
        created_at=NOW,
        updated_at=NOW,
    )


def seed_catalog() -> None:
    with SessionFactory.begin() as session:
        session.add(
            User(
                id=USER_ID,
                name="스냅샷 저장 사용자",
                login_id="Snapshot202",
                normalized_login_id="snapshot202",
                email="snapshot-202@example.com",
                normalized_email="snapshot-202@example.com",
                password_hash="not-a-real-password-hash",
                email_verified_at=NOW,
                status=UserStatus.ACTIVE.value,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.add_all(
            [
                product(SUPPLEMENT_ID, "SUPPLEMENT"),
                product(MEDICATION_ID, "MEDICATION"),
                product(EMPTY_SUPPLEMENT_ID, "SUPPLEMENT"),
                Nutrient(
                    id=ACTIVE_NUTRIENT_ID,
                    code="SNAPSHOT_ACTIVE_202",
                    name="활성 성분",
                    canonical_unit="MG",
                    is_active=True,
                ),
                Nutrient(
                    id=INACTIVE_NUTRIENT_ID,
                    code="SNAPSHOT_INACTIVE_203",
                    name="비활성 성분",
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
                    amount_per_unit=Decimal("10.2500"),
                    unit="MG",
                    sort_order=1,
                ),
                ProductNutrient(
                    product_id=SUPPLEMENT_ID,
                    nutrient_id=INACTIVE_NUTRIENT_ID,
                    amount_per_unit=Decimal("5.0000"),
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


def create_data(product_id: UUID) -> CareItemCreateData:
    return CareItemCreateData(
        user_id=USER_ID,
        product_id=product_id,
        purchase_date=date(2026, 8, 10),
        intake_start_date=date(2026, 8, 12),
        expected_depletion_date=date(2026, 9, 10),
        total_quantity=Decimal("60"),
        dose_per_intake=Decimal("1"),
        intakes_per_day=2,
        created_at=NOW,
    )


def snapshots_for(care_item_id: UUID) -> tuple[CareNutrientSnapshot, ...]:
    with SessionFactory() as session:
        return tuple(
            session.scalars(
                select(CareNutrientSnapshot)
                .where(CareNutrientSnapshot.care_item_id == care_item_id)
                .order_by(CareNutrientSnapshot.nutrient_id)
            )
        )


def test_supplement_snapshots_only_active_catalog_values_and_stays_immutable() -> None:
    seed_catalog()
    with SessionFactory() as session:
        created = SQLAlchemyCareItemRepository(session).create(
            create_data(SUPPLEMENT_ID)
        )

    assert created is not None
    snapshots = snapshots_for(created.id)
    assert len(snapshots) == 1
    assert snapshots[0].nutrient_id == ACTIVE_NUTRIENT_ID
    assert snapshots[0].nutrient_name == "활성 성분"
    assert snapshots[0].amount_per_unit == Decimal("10.2500")
    assert snapshots[0].unit == "MG"

    with SessionFactory.begin() as session:
        session.execute(
            update(ProductNutrient)
            .where(
                ProductNutrient.product_id == SUPPLEMENT_ID,
                ProductNutrient.nutrient_id == ACTIVE_NUTRIENT_ID,
            )
            .values(amount_per_unit=Decimal("1.5000"), unit="G")
        )
        session.execute(
            update(Nutrient)
            .where(Nutrient.id == ACTIVE_NUTRIENT_ID)
            .values(name="변경된 이름", is_active=False)
        )
        session.execute(
            delete(ProductNutrient).where(
                ProductNutrient.product_id == SUPPLEMENT_ID,
                ProductNutrient.nutrient_id == ACTIVE_NUTRIENT_ID,
            )
        )

    unchanged = snapshots_for(created.id)
    assert len(unchanged) == 1
    assert unchanged[0].nutrient_name == "활성 성분"
    assert unchanged[0].amount_per_unit == Decimal("10.2500")
    assert unchanged[0].unit == "MG"


@pytest.mark.parametrize("product_id", [MEDICATION_ID, EMPTY_SUPPLEMENT_ID])
def test_medication_or_supplement_without_active_nutrients_has_no_snapshot(
    product_id: UUID,
) -> None:
    seed_catalog()

    with SessionFactory() as session:
        created = SQLAlchemyCareItemRepository(session).create(create_data(product_id))

    assert created is not None
    assert snapshots_for(created.id) == ()


def test_repeated_registration_creates_independent_snapshot_sets() -> None:
    seed_catalog()

    with SessionFactory() as session:
        repository = SQLAlchemyCareItemRepository(session)
        first = repository.create(create_data(SUPPLEMENT_ID))
        second = repository.create(create_data(SUPPLEMENT_ID))

    assert first is not None
    assert second is not None
    assert first.id != second.id
    assert len(snapshots_for(first.id)) == 1
    assert len(snapshots_for(second.id)) == 1


def test_snapshot_flush_failure_rolls_back_item_and_snapshots() -> None:
    seed_catalog()

    def fail_after_flush(session: Session, flush_context: object) -> None:
        raise SQLAlchemyError("forced snapshot transaction failure")

    with SessionFactory() as session:
        event.listen(session, "after_flush_postexec", fail_after_flush)
        try:
            with pytest.raises(CareItemPersistenceError):
                SQLAlchemyCareItemRepository(session).create(create_data(SUPPLEMENT_ID))
        finally:
            event.remove(session, "after_flush_postexec", fail_after_flush)

    with SessionFactory() as session:
        item_count = session.scalar(
            select(func.count())
            .select_from(CareItem)
            .where(CareItem.user_id == USER_ID)
        )
        snapshot_count = session.scalar(
            select(func.count()).select_from(CareNutrientSnapshot)
        )
    assert item_count == 0
    assert snapshot_count == 0
