from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from allyakkkuk.auth.current_user_dependencies import require_current_user
from allyakkkuk.auth.current_user_service import AuthenticatedUser
from allyakkkuk.auth.models import Gender, User, UserStatus
from allyakkkuk.care.models import CareItem
from allyakkkuk.curation.models import Product
from allyakkkuk.db.session import SessionFactory, engine
from allyakkkuk.main import app
from allyakkkuk.medication.models import MedicationDetail
from allyakkkuk.seeding.runner import run_registered_seeds

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.10")]

NOW = datetime(2026, 8, 14, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000315")


def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        USER_ID,
        "MedicationAccept315",
        "의약품 인수 사용자",
        "medication-accept315@example.com",
        UserStatus.ACTIVE,
        NOW,
        date(1990, 1, 1),
        Gender.FEMALE,
        Decimal("165"),
        Decimal("55"),
        NOW,
        NOW,
    )


@pytest.fixture(autouse=True)
def medication_environment() -> Iterator[None]:
    run_registered_seeds(engine)
    app.dependency_overrides[require_current_user] = current_user
    _clean_user()
    with SessionFactory.begin() as session:
        session.add(
            User(
                id=USER_ID,
                name="의약품 인수 사용자",
                login_id="MedicationAccept315",
                normalized_login_id="medicationaccept315",
                email="medication-accept315@example.com",
                normalized_email="medication-accept315@example.com",
                password_hash="not-a-real-password-hash",
                email_verified_at=NOW,
                status=UserStatus.ACTIVE.value,
                created_at=NOW,
                updated_at=NOW,
            )
        )
    yield
    app.dependency_overrides.pop(require_current_user, None)
    _clean_user()


def _clean_user() -> None:
    with SessionFactory.begin() as session:
        session.execute(delete(CareItem).where(CareItem.user_id == USER_ID))
        session.execute(delete(User).where(User.id == USER_ID))


def test_user_selects_seeded_medication_and_reads_full_detail() -> None:
    with TestClient(app) as client:
        listing = client.get("/api/v1/medications")
        product_id = listing.json()["items"][0]["id"]
        detail = client.get(f"/api/v1/medications/{product_id}")

    assert listing.status_code == 200
    assert listing.json()["total"] == 2
    assert [row["sku"] for row in listing.json()["items"]] == [
        "LOCAL-MED-001",
        "LOCAL-MED-002",
    ]
    assert detail.status_code == 200
    assert detail.json()["source"]["name"].endswith("(실사용 금지)")
    assert detail.json()["precautions"].startswith("운영 전")


def test_seeded_medication_uses_existing_care_flow_but_not_nutrient_sum() -> None:
    with SessionFactory() as session:
        product_id = session.scalar(
            select(Product.id)
            .join(MedicationDetail, MedicationDetail.product_id == Product.id)
            .where(Product.sku == "LOCAL-MED-001")
        )
    assert product_id is not None

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/care/items",
            json={
                "product_id": str(product_id),
                "purchase_date": "2026-08-14",
                "intake_start_date": "2026-08-14",
                "total_quantity": "20",
                "dose_per_intake": "1",
                "intakes_per_day": 1,
            },
        )
        items = client.get("/api/v1/care/items")
        nutrients = client.get("/api/v1/care/daily-intake")

    assert created.status_code == 201
    assert items.status_code == 200
    assert items.json()["items"][0]["product_type"] == "MEDICATION"
    assert nutrients.status_code == 200
    assert nutrients.json()["nutrients"] == []
