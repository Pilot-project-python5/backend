from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from allyakkkuk.auth.current_user_dependencies import require_current_user
from allyakkkuk.auth.current_user_service import AuthenticatedUser
from allyakkkuk.auth.models import Gender, HealthProfile, User, UserStatus
from allyakkkuk.care.care_item_router import get_nutrient_status_service
from allyakkkuk.care.daily_intake_repository import SQLAlchemyDailyIntakeRepository
from allyakkkuk.care.daily_intake_service import DailyIntakeService
from allyakkkuk.care.models import CareItem, CareNutrientSnapshot
from allyakkkuk.care.nutrient_status_repository import (
    SQLAlchemyNutrientStatusRepository,
)
from allyakkkuk.care.nutrient_status_service import NutrientStatusService
from allyakkkuk.curation.models import Nutrient, Product
from allyakkkuk.db.session import SessionFactory, engine, get_db_session
from allyakkkuk.main import app
from allyakkkuk.ports.clock import FakeClock
from allyakkkuk.seeding.runner import run_registered_seeds

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.6")]

NOW = datetime(2026, 8, 14, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000362")
CARE_ITEM_ID = UUID("31000000-0000-4000-8000-000000000362")


def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        USER_ID,
        "StatusAccept362",
        "현황 인수 사용자",
        "status-accept-362@example.com",
        UserStatus.ACTIVE,
        NOW,
        date(1996, 8, 14),
        Gender.FEMALE,
        Decimal("165"),
        Decimal("55"),
        NOW,
        NOW,
    )


@pytest.fixture(autouse=True)
def status_environment() -> Iterator[None]:
    run_registered_seeds(engine)

    def status_service(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> NutrientStatusService:
        return NutrientStatusService(
            repository=SQLAlchemyNutrientStatusRepository(session),
            daily_intake_service=DailyIntakeService(
                SQLAlchemyDailyIntakeRepository(session)
            ),
            clock=FakeClock(NOW),
            time_zone=ZoneInfo("Asia/Seoul"),
            reference_version="KDRI-2025-20260316",
        )

    app.dependency_overrides[require_current_user] = current_user
    app.dependency_overrides[get_nutrient_status_service] = status_service
    _clean()
    _seed_user_plan()
    yield
    app.dependency_overrides.pop(require_current_user, None)
    app.dependency_overrides.pop(get_nutrient_status_service, None)
    _clean()


def _clean() -> None:
    with SessionFactory.begin() as session:
        session.execute(delete(CareItem).where(CareItem.user_id == USER_ID))
        session.execute(delete(User).where(User.id == USER_ID))


def _seed_user_plan() -> None:
    with SessionFactory.begin() as session:
        product_id = session.scalar(
            select(Product.id).where(
                Product.sku == "KORYO-EUNDAN-MULTIVITAMIN-ALL-IN-ONE"
            )
        )
        nutrients = {
            code: nutrient_id
            for code, nutrient_id in session.execute(
                select(Nutrient.code, Nutrient.id).where(
                    Nutrient.code.in_(["VITAMIN_C", "VITAMIN_D"])
                )
            )
        }
        assert product_id is not None
        session.add(
            User(
                id=USER_ID,
                name="현황 인수 사용자",
                login_id="StatusAccept362",
                normalized_login_id="statusaccept362",
                email="status-accept-362@example.com",
                normalized_email="status-accept-362@example.com",
                password_hash="not-a-real-password-hash",
                email_verified_at=NOW,
                status=UserStatus.ACTIVE.value,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.flush()
        session.add(
            HealthProfile(
                user_id=USER_ID,
                birth_date=date(1996, 8, 14),
                gender="FEMALE",
                height_cm=Decimal("165"),
                weight_kg=Decimal("55"),
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.add(
            CareItem(
                id=CARE_ITEM_ID,
                user_id=USER_ID,
                product_id=product_id,
                purchase_date=date(2026, 8, 10),
                intake_start_date=date(2026, 8, 14),
                expected_depletion_date=date(2026, 9, 12),
                total_quantity=Decimal("60"),
                quantity_unit="CAPSULE",
                dose_per_intake=Decimal("1"),
                intakes_per_day=2,
                created_at=NOW,
                updated_at=NOW,
                deleted_at=None,
            )
        )
        session.flush()
        session.add_all(
            [
                CareNutrientSnapshot(
                    id=UUID("32000000-0000-4000-8000-000000000362"),
                    care_item_id=CARE_ITEM_ID,
                    nutrient_id=nutrients["VITAMIN_C"],
                    nutrient_name="비타민 C",
                    amount_per_unit=Decimal("100"),
                    unit="MG",
                ),
                CareNutrientSnapshot(
                    id=UUID("32000000-0000-4000-8000-000000000363"),
                    care_item_id=CARE_ITEM_ID,
                    nutrient_id=nutrients["VITAMIN_D"],
                    nutrient_name="비타민 D",
                    amount_per_unit=Decimal("10"),
                    unit="MCG",
                ),
            ]
        )


def test_user_reads_age_gender_reference_comparison() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/care/nutrient-status")

    assert response.status_code == 200
    assert response.json()["age"] == 30
    assert [
        (row["nutrient_code"], row["reference_type"], row["achievement_rate_percent"])
        for row in response.json()["nutrients"]
    ] == [("VITAMIN_C", "RNI", "200"), ("VITAMIN_D", "AI", "200")]
