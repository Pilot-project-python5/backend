from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import delete, func, select

from yeongyangkkuk.auth.models import User, UserStatus
from yeongyangkkuk.care.care_item_repository import SQLAlchemyCareItemRepository
from yeongyangkkuk.care.models import CareItem, CareNutrientSnapshot
from yeongyangkkuk.curation.models import Nutrient, Product
from yeongyangkkuk.db.session import SessionFactory

pytestmark = [
    pytest.mark.integration,
    pytest.mark.feature("F-3.4"),
    pytest.mark.feature("F-3.11"),
]

NOW = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000216")
OTHER_USER_ID = UUID("11000000-0000-4000-8000-000000000217")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000216")
NUTRIENT_ID = UUID("23000000-0000-4000-8000-000000000216")
FIRST_ID = UUID("31000000-0000-4000-8000-000000000216")
LATEST_ID = UUID("31000000-0000-4000-8000-000000000217")
DELETED_ID = UUID("31000000-0000-4000-8000-000000000218")
OTHER_ID = UUID("31000000-0000-4000-8000-000000000219")
SNAPSHOT_ID = UUID("32000000-0000-4000-8000-000000000216")


@pytest.fixture(autouse=True)
def management_data() -> Iterator[None]:
    _clean_data()
    _seed_data()
    yield
    _clean_data()


def _clean_data() -> None:
    with SessionFactory.begin() as session:
        session.execute(
            delete(CareItem).where(CareItem.user_id.in_([USER_ID, OTHER_USER_ID]))
        )
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(Nutrient).where(Nutrient.id == NUTRIENT_ID))
        session.execute(delete(User).where(User.id.in_([USER_ID, OTHER_USER_ID])))


def _seed_data() -> None:
    with SessionFactory.begin() as session:
        for user_id, suffix in ((USER_ID, "216"), (OTHER_USER_ID, "217")):
            session.add(
                User(
                    id=user_id,
                    name=f"복용 관리 사용자 {suffix}",
                    login_id=f"CareManage{suffix}",
                    normalized_login_id=f"caremanage{suffix}",
                    email=f"care-manage-{suffix}@example.com",
                    normalized_email=f"care-manage-{suffix}@example.com",
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
                sku="CARE-MANAGE-216",
                product_type="SUPPLEMENT",
                brand="복용 관리 통합 브랜드",
                name="비게시 복용 관리 제품",
                image_url="/static/products/care-manage-216.svg",
                unit_form="CAPSULE",
                units_per_package=Decimal("60"),
                display_price=10000,
                is_published=False,
                sort_order=216,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.add(
            Nutrient(
                id=NUTRIENT_ID,
                code="CARE_MANAGE_NUTRIENT_216",
                name="복용 관리 성분",
                canonical_unit="MG",
                is_active=True,
            )
        )
        session.flush()
        session.add_all(
            [
                _item(FIRST_ID, USER_ID, NOW, Decimal("30")),
                _item(LATEST_ID, USER_ID, NOW, Decimal("60")),
                _item(
                    DELETED_ID,
                    USER_ID,
                    NOW - timedelta(minutes=2),
                    Decimal("90"),
                    deleted_at=NOW,
                ),
                _item(OTHER_ID, OTHER_USER_ID, NOW, Decimal("120")),
            ]
        )
        session.flush()
        session.add(
            CareNutrientSnapshot(
                id=SNAPSHOT_ID,
                care_item_id=LATEST_ID,
                nutrient_id=NUTRIENT_ID,
                nutrient_name="복용 관리 성분",
                amount_per_unit=Decimal("10"),
                unit="MG",
            )
        )


def _item(
    item_id: UUID,
    user_id: UUID,
    created_at: datetime,
    quantity: Decimal,
    *,
    deleted_at: datetime | None = None,
) -> CareItem:
    return CareItem(
        id=item_id,
        user_id=user_id,
        product_id=PRODUCT_ID,
        purchase_date=date(2026, 8, 10),
        intake_start_date=date(2026, 8, 13),
        expected_depletion_date=date(2026, 9, 11),
        total_quantity=quantity,
        quantity_unit="CAPSULE",
        dose_per_intake=Decimal("1"),
        intakes_per_day=2,
        created_at=created_at,
        updated_at=deleted_at or created_at,
        deleted_at=deleted_at,
    )


def test_repository_lists_only_owned_active_items_with_stable_pagination() -> None:
    with SessionFactory() as session:
        repository = SQLAlchemyCareItemRepository(session)
        first_page = repository.list_active(user_id=USER_ID, page=1, page_size=1)
        second_page = repository.list_active(user_id=USER_ID, page=2, page_size=1)
        empty_page = repository.list_active(user_id=USER_ID, page=3, page_size=1)

    assert first_page.total == second_page.total == empty_page.total == 2
    assert [item.id for item in first_page.items] == [LATEST_ID]
    assert [item.id for item in second_page.items] == [FIRST_ID]
    assert empty_page.items == ()
    assert first_page.items[0].name == "비게시 복용 관리 제품"
    assert first_page.items[0].total_quantity == Decimal("60")


def test_repository_soft_delete_preserves_item_and_snapshot_and_hides_ownership() -> (
    None
):
    with SessionFactory() as session:
        repository = SQLAlchemyCareItemRepository(session)
        deleted = repository.soft_delete(
            user_id=USER_ID,
            care_item_id=LATEST_ID,
            deleted_at=NOW + timedelta(minutes=1),
        )
        repeated = repository.soft_delete(
            user_id=USER_ID,
            care_item_id=LATEST_ID,
            deleted_at=NOW + timedelta(minutes=2),
        )
        other_owned = repository.soft_delete(
            user_id=USER_ID,
            care_item_id=OTHER_ID,
            deleted_at=NOW + timedelta(minutes=2),
        )

    assert deleted is True
    assert repeated is other_owned is False
    with SessionFactory() as session:
        stored = session.get(CareItem, LATEST_ID)
        snapshot_count = session.scalar(
            select(func.count())
            .select_from(CareNutrientSnapshot)
            .where(CareNutrientSnapshot.care_item_id == LATEST_ID)
        )
    assert stored is not None
    assert stored.deleted_at == NOW + timedelta(minutes=1)
    assert stored.updated_at == NOW + timedelta(minutes=1)
    assert snapshot_count == 1


def test_repository_updates_only_owned_active_item_expiration() -> None:
    expiration_date = date(2027, 1, 31)
    updated_at = NOW + timedelta(minutes=1)
    with SessionFactory() as session:
        repository = SQLAlchemyCareItemRepository(session)
        updated = repository.update_expiration(
            user_id=USER_ID,
            care_item_id=LATEST_ID,
            expiration_date=expiration_date,
            updated_at=updated_at,
        )
        other_owned = repository.update_expiration(
            user_id=USER_ID,
            care_item_id=OTHER_ID,
            expiration_date=expiration_date,
            updated_at=updated_at,
        )
        deleted = repository.update_expiration(
            user_id=USER_ID,
            care_item_id=DELETED_ID,
            expiration_date=expiration_date,
            updated_at=updated_at,
        )

    assert updated is True
    assert other_owned is deleted is False
    with SessionFactory() as session:
        stored = session.get(CareItem, LATEST_ID)
    assert stored is not None
    assert stored.expiration_date == expiration_date
    assert stored.updated_at == updated_at
