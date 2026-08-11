from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from allyakkkuk.auth.tokens import JwtSessionTokenIssuer, parse_refresh_token

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-1.3")]

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
SESSION_ID = UUID("22222222-2222-4222-8222-222222222222")
SECRET = "unit-test-session-token-secret-at-least-32-characters"


def test_login_refresh_token_contains_session_selector_and_secret() -> None:
    issuer = JwtSessionTokenIssuer(SECRET)

    tokens = issuer.issue(USER_ID, SESSION_ID, NOW)
    parts = parse_refresh_token(tokens.refresh_token)

    assert parts is not None
    assert parts.session_id == SESSION_ID
    assert len(parts.secret) >= 64
    assert issuer.verify_refresh_token(
        SESSION_ID,
        tokens.refresh_token,
        tokens.refresh_token_hash,
    )


@pytest.mark.parametrize(
    "raw_token",
    [
        None,
        "",
        "legacy-token-without-selector",
        f"not-a-uuid.{'a' * 64}",
        f"{SESSION_ID}.short",
        f"{SESSION_ID}.{'a' * 64}.extra",
    ],
)
def test_malformed_refresh_token_is_rejected(raw_token: str | None) -> None:
    assert parse_refresh_token(raw_token) is None


def test_rotation_preserves_absolute_expiration_and_changes_secret() -> None:
    issuer = JwtSessionTokenIssuer(SECRET)
    original = issuer.issue(USER_ID, SESSION_ID, NOW)
    rotation_time = NOW + timedelta(hours=1)

    rotated = issuer.rotate(
        USER_ID,
        SESSION_ID,
        rotation_time,
        original.refresh_token_expires_at,
    )

    original_parts = parse_refresh_token(original.refresh_token)
    rotated_parts = parse_refresh_token(rotated.refresh_token)
    assert original_parts is not None
    assert rotated_parts is not None
    assert rotated_parts.session_id == original_parts.session_id == SESSION_ID
    assert rotated_parts.secret != original_parts.secret
    assert rotated.access_token_expires_at == rotation_time + timedelta(minutes=15)
    assert rotated.refresh_token_expires_at == original.refresh_token_expires_at
    assert issuer.verify_refresh_token(
        SESSION_ID,
        rotated.refresh_token,
        rotated.refresh_token_hash,
    )
    assert not issuer.verify_refresh_token(
        SESSION_ID,
        original.refresh_token,
        rotated.refresh_token_hash,
    )
