from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from yeongyangkkuk.auth.current_user_dependencies import require_current_user
from yeongyangkkuk.auth.current_user_service import AuthenticatedUser
from yeongyangkkuk.auth.models import Gender, User, UserStatus
from yeongyangkkuk.care.models import CareItem, CareNutrientSnapshot
from yeongyangkkuk.curation.models import Nutrient, Product
from yeongyangkkuk.db.session import SessionFactory
from yeongyangkkuk.main import app

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.5")]

NOW = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000354")
OTHER_USER_ID = UUID("11000000-0000-4000-8000-000000000355")
SUPPLEMENT_ID = UUID("22000000-0000-4000-8000-000000000354")
MEDICATION_ID = UUID("22000000-0000-4000-8000-000000000355")
VITAMIN_C_ID = UUID("23000000-0000-4000-8000-000000000355")
VITAMIN_D_ID = UUID("23000000-0000-4000-8000-000000000356")


def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=USER_ID,
        login_id="DailyAccept354",
        name="일일 섭취량 인수 사용자",
        email="daily-accept-354@example.com",
        status=UserStatus.ACTIVE,
        email_verified_at=NOW,
        birth_date=date(1990, 1, 1),
        gender=Gender.MALE,
        height_cm=Decimal("175"),
        weight_kg=Decimal("70"),
        access_token_expires_at=NOW,
        refresh_token_expires_at=NOW,
    )


@pytest.fixture(autouse=True)
def daily_intake_environment() -> Iterator[None]:
    app.dependency_overrides[require_current_user] = current_user
    _clean_data()
    _seed_data()
    yield
    app.dependency_overrides.pop(require_current_user, None)
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
        session.add_all([_user(USER_ID, "354"), _user(OTHER_USER_ID, "355")])
        session.add_all(
            [
                _product(SUPPLEMENT_ID, "DAILY-ACCEPT-SUPPLEMENT-354", "SUPPLEMENT"),
                _product(MEDICATION_ID, "DAILY-ACCEPT-MEDICATION-355", "MEDICATION"),
            ]
        )
        session.add_all(
            [
                Nutrient(
                    id=VITAMIN_C_ID,
                    code="VITAMIN_C_ACCEPT_355",
                    name="비타민 C",
                    canonical_unit="MG",
                    is_active=True,
                ),
                Nutrient(
                    id=VITAMIN_D_ID,
                    code="VITAMIN_D_ACCEPT_356",
                    name="비타민 D",
                    canonical_unit="IU",
                    is_active=False,
                ),
            ]
        )
        session.flush()
        items = [
            _item(1, USER_ID, SUPPLEMENT_ID, "2", 2),
            _item(2, USER_ID, SUPPLEMENT_ID, "0.5", 1, start=date(2026, 9, 1)),
            _item(3, USER_ID, SUPPLEMENT_ID, "10", 10, deleted_at=NOW),
            _item(4, OTHER_USER_ID, SUPPLEMENT_ID, "10", 10),
            _item(5, USER_ID, MEDICATION_ID, "10", 10),
        ]
        session.add_all(items)
        session.flush()
        session.add_all(
            [
                _snapshot(1, items[0].id, VITAMIN_C_ID, "0.5", "G"),
                _snapshot(2, items[1].id, VITAMIN_C_ID, "300", "MG"),
                _snapshot(3, items[1].id, VITAMIN_D_ID, "400", "IU"),
                _snapshot(4, items[2].id, VITAMIN_C_ID, "999", "G"),
                _snapshot(5, items[3].id, VITAMIN_C_ID, "999", "G"),
                _snapshot(6, items[4].id, VITAMIN_C_ID, "999", "G"),
            ]
        )


def _user(user_id: UUID, suffix: str) -> User:
    return User(
        id=user_id,
        name=f"일일 섭취량 인수 사용자 {suffix}",
        login_id=f"DailyAccept{suffix}",
        normalized_login_id=f"dailyaccept{suffix}",
        email=f"daily-accept-{suffix}@example.com",
        normalized_email=f"daily-accept-{suffix}@example.com",
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
        brand="일일 섭취량 인수 브랜드",
        name=sku,
        image_url=f"/static/products/{sku.lower()}.svg",
        unit_form="CAPSULE",
        units_per_package=Decimal("60"),
        display_price=0,
        is_published=True,
        sort_order=354,
        created_at=NOW,
        updated_at=NOW,
    )


def _item(
    sequence: int,
    user_id: UUID,
    product_id: UUID,
    dose: str,
    times: int,
    *,
    start: date = date(2026, 8, 13),
    deleted_at: datetime | None = None,
) -> CareItem:
    return CareItem(
        id=UUID(f"31000000-0000-4000-8000-{sequence + 360:012d}"),
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
        id=UUID(f"32000000-0000-4000-8000-{sequence + 360:012d}"),
        care_item_id=item_id,
        nutrient_id=nutrient_id,
        nutrient_name="등록 당시 이름",
        amount_per_unit=Decimal(amount),
        unit=unit,
    )


def test_user_reads_aggregated_active_supplement_daily_plan() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/care/daily-intake")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "nutrients": [
            {
                "nutrient_id": str(VITAMIN_C_ID),
                "nutrient_code": "VITAMIN_C_ACCEPT_355",
                "nutrient_name": "비타민 C",
                "daily_amount": "2150",
                "unit": "MG",
            },
            {
                "nutrient_id": str(VITAMIN_D_ID),
                "nutrient_code": "VITAMIN_D_ACCEPT_356",
                "nutrient_name": "비타민 D",
                "daily_amount": "200",
                "unit": "IU",
            },
        ]
    }


def test_user_without_active_snapshots_receives_empty_result() -> None:
    with SessionFactory.begin() as session:
        session.execute(delete(CareItem).where(CareItem.user_id == USER_ID))

    with TestClient(app) as client:
        response = client.get("/api/v1/care/daily-intake")

    assert response.status_code == 200
    assert response.json() == {"nutrients": []}
