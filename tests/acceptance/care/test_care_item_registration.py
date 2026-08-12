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

from allyakkkuk.auth.current_user_dependencies import get_current_user_service
from allyakkkuk.auth.current_user_repository import SQLAlchemyCurrentUserRepository
from allyakkkuk.auth.current_user_service import CurrentUserService
from allyakkkuk.auth.login_repository import SQLAlchemyLoginRepository
from allyakkkuk.auth.login_router import get_login_service
from allyakkkuk.auth.login_service import LoginService
from allyakkkuk.auth.models import Gender, HealthProfile, User, UserStatus
from allyakkkuk.auth.passwords import Argon2PasswordHasher
from allyakkkuk.auth.tokens import JwtSessionTokenIssuer
from allyakkkuk.care.care_item_repository import SQLAlchemyCareItemRepository
from allyakkkuk.care.care_item_router import get_care_item_service
from allyakkkuk.care.care_item_service import CareItemService
from allyakkkuk.care.models import CareItem
from allyakkkuk.curation.models import Product
from allyakkkuk.db.session import SessionFactory, get_db_session
from allyakkkuk.main import app
from allyakkkuk.ports.clock import FakeClock

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.1")]

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
USER_ID = UUID("11000000-0000-4000-8000-000000000033")
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000033")
PASSWORD = "Safe!Pass123"
PASSWORD_HASHER = Argon2PasswordHasher()
DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash("Dummy!Pass123")
TOKEN_SECRET = "acceptance-test-care-token-secret-at-least-32-characters"


@pytest.fixture(autouse=True)
def local_care_environment() -> Iterator[None]:
    clock = FakeClock(NOW)
    token_issuer = JwtSessionTokenIssuer(TOKEN_SECRET)

    def login_service(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> LoginService:
        return LoginService(
            repository=SQLAlchemyLoginRepository(session),
            password_hasher=PASSWORD_HASHER,
            dummy_password_hash=DUMMY_PASSWORD_HASH,
            token_issuer=token_issuer,
            clock=clock,
        )

    def current_service(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> CurrentUserService:
        return CurrentUserService(
            repository=SQLAlchemyCurrentUserRepository(session),
            token_verifier=token_issuer,
            clock=clock,
        )

    def care_service(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> CareItemService:
        return CareItemService(
            SQLAlchemyCareItemRepository(session),
            clock,
            ZoneInfo("Asia/Seoul"),
        )

    app.dependency_overrides[get_login_service] = login_service
    app.dependency_overrides[get_current_user_service] = current_service
    app.dependency_overrides[get_care_item_service] = care_service
    with SessionFactory.begin() as session:
        session.execute(delete(CareItem))
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(User).where(User.id == USER_ID))
        session.add(
            User(
                id=USER_ID,
                name="복용 인수 사용자",
                login_id="CareAccept33",
                normalized_login_id="careaccept33",
                email="care-accept33@example.com",
                normalized_email="care-accept33@example.com",
                password_hash=PASSWORD_HASHER.hash(PASSWORD),
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
                birth_date=date(1995, 5, 20),
                gender=Gender.MALE.value,
                height_cm=Decimal("175"),
                weight_kg=Decimal("70"),
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.add(
            Product(
                id=PRODUCT_ID,
                sku="CARE-ACCEPT-33",
                product_type="SUPPLEMENT",
                brand="복용 인수 브랜드",
                name="복용 인수 제품",
                image_url="/static/products/care-accept-33.svg",
                unit_form="CAPSULE",
                units_per_package=Decimal("60"),
                display_price=10000,
                is_published=True,
                sort_order=33,
                created_at=NOW,
                updated_at=NOW,
            )
        )
    yield
    app.dependency_overrides.pop(get_login_service, None)
    app.dependency_overrides.pop(get_current_user_service, None)
    app.dependency_overrides.pop(get_care_item_service, None)
    with SessionFactory.begin() as session:
        session.execute(delete(CareItem))
        session.execute(delete(Product).where(Product.id == PRODUCT_ID))
        session.execute(delete(User).where(User.id == USER_ID))


def test_logged_in_user_registers_same_catalog_product_as_distinct_history() -> None:
    payload = {
        "product_id": str(PRODUCT_ID),
        "purchase_date": "2026-08-10",
        "intake_start_date": "2026-08-12",
        "total_quantity": "60",
        "dose_per_intake": "1",
        "intakes_per_day": 2,
    }
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"login_id": "CareAccept33", "password": PASSWORD},
        )
        first = client.post("/api/v1/care/items", json=payload)
        second = client.post("/api/v1/care/items", json=payload)

    assert login.status_code == 200
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    with SessionFactory() as session:
        stored = tuple(
            session.scalars(
                select(CareItem)
                .where(CareItem.user_id == USER_ID)
                .order_by(CareItem.id)
            )
        )
    assert len(stored) == 2
    assert all(item.product_id == PRODUCT_ID for item in stored)
    assert all(item.total_quantity == Decimal("60") for item in stored)
