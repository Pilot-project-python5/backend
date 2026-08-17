from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import delete, func, select

from yeongyangkkuk.auth.models import User, UserStatus
from yeongyangkkuk.care.daily_intake_repository import SQLAlchemyDailyIntakeRepository
from yeongyangkkuk.care.models import CareItem, CareNutrientSnapshot
from yeongyangkkuk.curation.models import Nutrient, Product
from yeongyangkkuk.db.session import SessionFactory

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.5")]

NOW = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000352")
OTHER_USER_ID = UUID("11000000-0000-4000-8000-000000000353")
SUPPLEMENT_ID = UUID("22000000-0000-4000-8000-000000000352")
MEDICATION_ID = UUID("22000000-0000-4000-8000-000000000353")
VITAMIN_C_ID = UUID("23000000-0000-4000-8000-000000000353")
VITAMIN_D_ID = UUID("23000000-0000-4000-8000-000000000354")
ITEM_ONE_ID = UUID("31000000-0000-4000-8000-000000000352")
ITEM_TWO_ID = UUID("31000000-0000-4000-8000-000000000353")
DELETED_ID = UUID("31000000-0000-4000-8000-000000000354")
OTHER_ITEM_ID = UUID("31000000-0000-4000-8000-000000000355")
MEDICATION_ITEM_ID = UUID("31000000-0000-4000-8000-000000000356")


@pytest.fixture(autouse=True)
def daily_intake_data() -> Iterator[None]:
    _clean_data()
    _seed_data()
    yield
    _clean_data()


def _clean_data() -> None:
    with SessionFactory.begin() as session:
        session.execute(
            delete(CareItem).where(CareItem.user_id.in_([USER_ID, OTHER_USER_ID]))
        )
        session.execute(
            delete(Product).where(Product.id.in_([SUPPLEMENT_ID, MEDICATION_ID]))
        )
        session.execute(
            delete(Nutrient).where(Nutrient.id.in_([VITAMIN_C_ID, VITAMIN_D_ID]))
        )
        session.execute(delete(User).where(User.id.in_([USER_ID, OTHER_USER_ID])))


def _seed_data() -> None:
    with SessionFactory.begin() as session:
        session.add_all([_user(USER_ID, "352"), _user(OTHER_USER_ID, "353")])
        session.add_all(
            [
                _product(SUPPLEMENT_ID, "DAILY-INTAKE-SUPPLEMENT-352", "SUPPLEMENT"),
                _product(MEDICATION_ID, "DAILY-INTAKE-MEDICATION-353", "MEDICATION"),
            ]
        )
        session.add_all(
            [
                Nutrient(
                    id=VITAMIN_C_ID,
                    code="DAILY_VITAMIN_C_353",
                    name="일일 비타민 C",
                    canonical_unit="MG",
                    is_active=False,
                ),
                Nutrient(
                    id=VITAMIN_D_ID,
                    code="DAILY_VITAMIN_D_354",
                    name="일일 비타민 D",
                    canonical_unit="IU",
                    is_active=True,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                _item(ITEM_ONE_ID, USER_ID, SUPPLEMENT_ID, dose="2", times=2),
                _item(
                    ITEM_TWO_ID,
                    USER_ID,
                    SUPPLEMENT_ID,
                    dose="0.5",
                    times=1,
                    start=date(2026, 9, 1),
                ),
                _item(
                    DELETED_ID,
                    USER_ID,
                    SUPPLEMENT_ID,
                    dose="10",
                    times=10,
                    deleted_at=NOW,
                ),
                _item(
                    OTHER_ITEM_ID,
                    OTHER_USER_ID,
                    SUPPLEMENT_ID,
                    dose="10",
                    times=10,
                ),
                _item(
                    MEDICATION_ITEM_ID,
                    USER_ID,
                    MEDICATION_ID,
                    dose="10",
                    times=10,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                _snapshot(1, ITEM_ONE_ID, VITAMIN_C_ID, "0.5", "G"),
                _snapshot(2, ITEM_TWO_ID, VITAMIN_C_ID, "200", "MG"),
                _snapshot(3, ITEM_TWO_ID, VITAMIN_D_ID, "400", "IU"),
                _snapshot(4, DELETED_ID, VITAMIN_C_ID, "999", "G"),
                _snapshot(5, OTHER_ITEM_ID, VITAMIN_C_ID, "999", "G"),
                _snapshot(6, MEDICATION_ITEM_ID, VITAMIN_C_ID, "999", "G"),
            ]
        )


def _user(user_id: UUID, suffix: str) -> User:
    return User(
        id=user_id,
        name=f"일일 섭취량 사용자 {suffix}",
        login_id=f"DailyIntake{suffix}",
        normalized_login_id=f"dailyintake{suffix}",
        email=f"daily-intake-{suffix}@example.com",
        normalized_email=f"daily-intake-{suffix}@example.com",
        password_hash="not-a-real-password-hash",
        email_verified_at=NOW,
        status=UserStatus.ACTIVE.value,
        created_at=NOW,
        updated_at=NOW,
    )


def _product(product_id: UUID, sku: str, product_type: str) -> Product:
    return Product(
        id=product_id,
        sku=sku,
        product_type=product_type,
        brand="일일 섭취량 브랜드",
        name=sku,
        image_url=f"/static/products/{sku.lower()}.svg",
        unit_form="CAPSULE",
        units_per_package=Decimal("60"),
        display_price=0,
        is_published=True,
        sort_order=352,
        created_at=NOW,
        updated_at=NOW,
    )


def _item(
    item_id: UUID,
    user_id: UUID,
    product_id: UUID,
    *,
    dose: str,
    times: int,
    start: date = date(2026, 8, 13),
    deleted_at: datetime | None = None,
) -> CareItem:
    return CareItem(
        id=item_id,
        user_id=user_id,
        product_id=product_id,
        purchase_date=date(2026, 8, 10),
        intake_start_date=start,
        expected_depletion_date=start + timedelta(days=29),
        total_quantity=Decimal("60"),
        quantity_unit="CAPSULE",
        dose_per_intake=Decimal(dose),
        intakes_per_day=times,
        created_at=NOW - timedelta(days=1),
        updated_at=deleted_at or NOW - timedelta(days=1),
        deleted_at=deleted_at,
    )


def _snapshot(
    sequence: int,
    item_id: UUID,
    nutrient_id: UUID,
    amount: str,
    unit: str,
) -> CareNutrientSnapshot:
    return CareNutrientSnapshot(
        id=UUID(f"32000000-0000-4000-8000-{sequence:012d}"),
        care_item_id=item_id,
        nutrient_id=nutrient_id,
        nutrient_name="등록 당시 성분명",
        amount_per_unit=Decimal(amount),
        unit=unit,
    )


def test_repository_returns_only_owned_active_supplement_snapshot_plans() -> None:
    with SessionFactory() as session:
        rows = SQLAlchemyDailyIntakeRepository(session).list_active_nutrient_plans(
            user_id=USER_ID
        )

    assert [row.nutrient_code for row in rows] == [
        "DAILY_VITAMIN_C_353",
        "DAILY_VITAMIN_C_353",
        "DAILY_VITAMIN_D_354",
    ]
    assert [(row.amount_per_unit, row.dose_per_intake) for row in rows] == [
        (Decimal("0.5000"), Decimal("2.000")),
        (Decimal("200.0000"), Decimal("0.500")),
        (Decimal("400.0000"), Decimal("0.500")),
    ]
    assert rows[0].canonical_unit == "MG"
    assert rows[0].nutrient_name == "일일 비타민 C"


def test_repository_read_does_not_change_persistent_rows() -> None:
    with SessionFactory() as session:
        before = session.scalar(select(func.count()).select_from(CareItem))
        SQLAlchemyDailyIntakeRepository(session).list_active_nutrient_plans(
            user_id=USER_ID
        )
        after = session.scalar(select(func.count()).select_from(CareItem))

    assert before == after
