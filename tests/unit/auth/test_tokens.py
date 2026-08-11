from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest

from allyakkkuk.auth.tokens import JwtSessionTokenIssuer

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-1.2")]

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
SESSION_ID = UUID("22222222-2222-4222-8222-222222222222")
SECRET = "unit-test-auth-token-secret-at-least-32-characters"


def test_token_issuer_rejects_short_secret() -> None:
    with pytest.raises(ValueError, match="32자 이상"):
        JwtSessionTokenIssuer("too-short")


def test_token_issuer_creates_expected_access_claims_and_lifetimes() -> None:
    issuer = JwtSessionTokenIssuer(SECRET)

    tokens = issuer.issue(USER_ID, SESSION_ID, NOW)
    claims = jwt.decode(
        tokens.access_token,
        SECRET,
        algorithms=["HS256"],
        audience="allyakkkuk-api",
        issuer="allyakkkuk",
        options={"verify_iat": False},
    )

    assert claims["sub"] == str(USER_ID)
    assert claims["sid"] == str(SESSION_ID)
    assert claims["type"] == "access"
    assert UUID(claims["jti"])
    assert datetime.fromtimestamp(claims["iat"], UTC) == NOW
    assert datetime.fromtimestamp(claims["exp"], UTC) == NOW + timedelta(minutes=15)
    assert tokens.access_token_expires_at == NOW + timedelta(minutes=15)
    assert tokens.refresh_token_expires_at == NOW + timedelta(days=14)


def test_refresh_token_is_high_entropy_and_only_hash_is_verifiable() -> None:
    issuer = JwtSessionTokenIssuer(SECRET)

    first = issuer.issue(USER_ID, SESSION_ID, NOW)
    second = issuer.issue(USER_ID, SESSION_ID, NOW)

    assert len(first.refresh_token) >= 64
    assert first.refresh_token != second.refresh_token
    assert first.refresh_token not in first.refresh_token_hash
    assert len(first.refresh_token_hash) == 64
    assert issuer.verify_refresh_token(
        SESSION_ID,
        first.refresh_token,
        first.refresh_token_hash,
    )
    assert not issuer.verify_refresh_token(
        SESSION_ID,
        second.refresh_token,
        first.refresh_token_hash,
    )
