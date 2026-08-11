from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest

from allyakkkuk.auth.tokens import (
    ACCESS_TOKEN_AUDIENCE,
    ACCESS_TOKEN_ISSUER,
    JwtSessionTokenIssuer,
)

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-1.4")]

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
SESSION_ID = UUID("22222222-2222-4222-8222-222222222222")
TOKEN_ID = UUID("33333333-3333-4333-8333-333333333333")
SECRET = "unit-test-access-token-secret-at-least-32-characters"


def claims(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "iss": ACCESS_TOKEN_ISSUER,
        "aud": ACCESS_TOKEN_AUDIENCE,
        "sub": str(USER_ID),
        "sid": str(SESSION_ID),
        "type": "access",
        "jti": str(TOKEN_ID),
        "iat": int(NOW.timestamp()),
        "exp": int((NOW + timedelta(minutes=15)).timestamp()),
    }
    values.update(overrides)
    return values


def encode(payload: dict[str, object], *, secret: str = SECRET) -> str:
    return jwt.encode(payload, secret, algorithm="HS256")


def test_issued_access_token_verifies_required_claims() -> None:
    issuer = JwtSessionTokenIssuer(SECRET)
    issued = issuer.issue(USER_ID, SESSION_ID, NOW)

    verified = issuer.verify_access_token(issued.access_token, NOW)

    assert verified is not None
    assert verified.user_id == USER_ID
    assert verified.session_id == SESSION_ID
    assert verified.issued_at == NOW
    assert verified.expires_at == NOW + timedelta(minutes=15)


@pytest.mark.parametrize(
    "raw_token",
    [
        None,
        "",
        "not-a-jwt",
        encode(claims(), secret="another-access-token-secret-at-least-32-characters"),
        encode(claims(iss="another-issuer")),
        encode(claims(aud="another-audience")),
        encode(claims(type="refresh")),
        encode(claims(sub="not-a-uuid")),
        encode(claims(sid="not-a-uuid")),
        encode(claims(jti="not-a-uuid")),
        encode(claims(iat=int((NOW + timedelta(seconds=1)).timestamp()))),
        encode(claims(exp=int(NOW.timestamp()))),
        encode(claims(exp=10**100)),
    ],
)
def test_invalid_access_token_reasons_are_rejected(raw_token: str | None) -> None:
    issuer = JwtSessionTokenIssuer(SECRET)

    assert issuer.verify_access_token(raw_token, NOW) is None


@pytest.mark.parametrize("missing_claim", ["sub", "sid", "jti", "iat", "exp"])
def test_missing_required_claim_is_rejected(missing_claim: str) -> None:
    issuer = JwtSessionTokenIssuer(SECRET)
    payload = claims()
    payload.pop(missing_claim)

    assert issuer.verify_access_token(encode(payload), NOW) is None
