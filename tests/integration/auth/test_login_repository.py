from __future__ import annotations

import pytest
from sqlalchemy import inspect

from allyakkkuk.db.session import engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-1.2")]


def test_refresh_session_schema_has_expected_constraints_and_indexes() -> None:
    inspector = inspect(engine)

    uniques = {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints("refresh_sessions")
    }
    checks = {
        item["name"] for item in inspector.get_check_constraints("refresh_sessions")
    }
    foreign_keys = inspector.get_foreign_keys("refresh_sessions")
    indexes = inspector.get_indexes("refresh_sessions")

    assert ("token_hash",) in uniques
    assert {
        "ck_refresh_sessions_expires_at",
        "ck_refresh_sessions_revoked_at",
        "ck_refresh_sessions_last_used_at",
    } <= checks
    assert any(
        key["referred_table"] == "users"
        and key["constrained_columns"] == ["user_id"]
        and key["options"].get("ondelete") == "CASCADE"
        for key in foreign_keys
    )
    assert any(
        item["name"] == "ix_refresh_sessions_user_created_at"
        and item["column_names"] == ["user_id", "created_at"]
        for item in indexes
    )
    assert any(
        item["name"] == "ix_refresh_sessions_expires_at"
        and item["column_names"] == ["expires_at"]
        for item in indexes
    )
