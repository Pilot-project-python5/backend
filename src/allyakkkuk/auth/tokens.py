"""로그인 세션용 access·refresh token 발급과 검증."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

import jwt

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=14)
ACCESS_TOKEN_ISSUER = "allyakkkuk"
ACCESS_TOKEN_AUDIENCE = "allyakkkuk-api"


@dataclass(frozen=True, slots=True)
class IssuedSessionTokens:
    access_token: str
    refresh_token: str
    refresh_token_hash: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


class SessionTokenIssuer(Protocol):
    def issue(
        self, user_id: UUID, session_id: UUID, issued_at: datetime
    ) -> IssuedSessionTokens: ...


class JwtSessionTokenIssuer:
    """HS256 access token과 불투명 refresh token을 함께 발급한다."""

    def __init__(self, secret: str) -> None:
        if len(secret) < 32:
            raise ValueError("token secret은 32자 이상이어야 합니다")
        self._secret = secret.encode()

    def issue(
        self, user_id: UUID, session_id: UUID, issued_at: datetime
    ) -> IssuedSessionTokens:
        access_expires_at = issued_at + ACCESS_TOKEN_TTL
        refresh_expires_at = issued_at + REFRESH_TOKEN_TTL
        access_token = jwt.encode(
            {
                "iss": ACCESS_TOKEN_ISSUER,
                "aud": ACCESS_TOKEN_AUDIENCE,
                "sub": str(user_id),
                "sid": str(session_id),
                "type": "access",
                "jti": str(uuid4()),
                "iat": issued_at,
                "exp": access_expires_at,
            },
            self._secret,
            algorithm="HS256",
        )
        refresh_token = secrets.token_urlsafe(48)
        return IssuedSessionTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            refresh_token_hash=self._hash_refresh_token(session_id, refresh_token),
            access_token_expires_at=access_expires_at,
            refresh_token_expires_at=refresh_expires_at,
        )

    def verify_refresh_token(
        self,
        session_id: UUID,
        refresh_token: str,
        expected_hash: str,
    ) -> bool:
        candidate_hash = self._hash_refresh_token(session_id, refresh_token)
        return hmac.compare_digest(candidate_hash, expected_hash)

    def _hash_refresh_token(self, session_id: UUID, refresh_token: str) -> str:
        message = f"refresh:{session_id}:{refresh_token}".encode()
        return hmac.new(self._secret, message, hashlib.sha256).hexdigest()
