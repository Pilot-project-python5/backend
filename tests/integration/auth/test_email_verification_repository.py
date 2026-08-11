from __future__ import annotations

import pytest
from sqlalchemy import inspect

from allyakkkuk.db.session import engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-1.1.3")]


def test_email_verification_schema_has_expected_constraints_and_index() -> None:
    inspector = inspect(engine)

    checks = {
        item["name"] for item in inspector.get_check_constraints("email_verifications")
    }
    foreign_keys = inspector.get_foreign_keys("email_verifications")
    indexes = inspector.get_indexes("email_verifications")

    assert {
        "ck_email_verifications_purpose",
        "ck_email_verifications_failed_attempts",
        "ck_email_verifications_expires_at",
        "ck_email_verifications_resend_available_at",
        "ck_email_verifications_used_at",
        "ck_email_verifications_superseded_at",
        "ck_email_verifications_terminal_state",
    } <= checks
    assert any(
        key["referred_table"] == "users"
        and key["constrained_columns"] == ["user_id"]
        and key["options"].get("ondelete") == "CASCADE"
        for key in foreign_keys
    )
    assert any(
        item["name"] == "ix_email_verifications_user_created_at"
        and item["column_names"] == ["user_id", "created_at"]
        for item in indexes
    )
