from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import delete, inspect, select

from yeongyangkkuk.auth.models import Gender, HealthProfile, User
from yeongyangkkuk.auth.repository import (
    SignupData,
    SignupPersistenceError,
    SQLAlchemySignupRepository,
)
from yeongyangkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-1.1")]


def test_signup_repository_rolls_back_user_when_profile_fails() -> None:
    with SessionFactory.begin() as cleanup:
        cleanup.execute(delete(HealthProfile))
        cleanup.execute(delete(User))

    data = SignupData(
        name="롤백 사용자",
        login_id="Rollback1",
        normalized_login_id="rollback1",
        email="rollback@example.com",
        normalized_email="rollback@example.com",
        password_hash="$argon2id$fixture",
        birth_date=date(1990, 1, 1),
        gender=Gender.MALE,
        height_cm=Decimal("251"),
        weight_kg=Decimal("70"),
        created_at=datetime(2026, 8, 10, 9, 0, tzinfo=UTC),
    )

    with SessionFactory() as session:
        repository = SQLAlchemySignupRepository(session)
        with pytest.raises(SignupPersistenceError):
            repository.create(data)

    with SessionFactory() as session:
        user = session.scalar(
            select(User).where(User.normalized_login_id == "rollback1")
        )
    assert user is None


def test_signup_schema_has_expected_constraints() -> None:
    inspector = inspect(engine)

    user_uniques = {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints("users")
    }
    profile_checks = {
        item["name"] for item in inspector.get_check_constraints("health_profiles")
    }
    profile_foreign_keys = inspector.get_foreign_keys("health_profiles")

    assert ("normalized_login_id",) in user_uniques
    assert ("normalized_email",) in user_uniques
    assert {
        "ck_health_profiles_gender",
        "ck_health_profiles_height_range",
        "ck_health_profiles_weight_range",
    } <= profile_checks
    assert any(
        key["referred_table"] == "users"
        and key["constrained_columns"] == ["user_id"]
        and key["options"].get("ondelete") == "CASCADE"
        for key in profile_foreign_keys
    )
