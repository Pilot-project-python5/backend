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


@dataclass(frozen=True, slots=True)
class RefreshTokenParts:
    session_id: UUID
    secret: str


class SessionTokenIssuer(Protocol):
    def issue(
        self, user_id: UUID, session_id: UUID, issued_at: datetime
    ) -> IssuedSessionTokens: ...


class SessionTokenRotator(Protocol):
    def parse_refresh_token(
        self, raw_token: str | None
    ) -> RefreshTokenParts | None: ...

    def verify_refresh_token(
        self,
        session_id: UUID,
        refresh_token: str,
        expected_hash: str,
    ) -> bool: ...

    def rotate(
        self,
        user_id: UUID,
        session_id: UUID,
        issued_at: datetime,
        refresh_token_expires_at: datetime,
    ) -> IssuedSessionTokens: ...


def parse_refresh_token(raw_token: str | None) -> RefreshTokenParts | None:
    if raw_token is None or raw_token.count(".") != 1:
        return None
    selector, secret = raw_token.split(".", maxsplit=1)
    if len(secret) < 64:
        return None
    try:
        session_id = UUID(selector)
    except ValueError:
        return None
    return RefreshTokenParts(session_id=session_id, secret=secret)


class JwtSessionTokenIssuer:
    """HS256 access token과 불투명 refresh token을 함께 발급한다."""

    def __init__(self, secret: str) -> None:
        if len(secret) < 32:
            raise ValueError("token secret은 32자 이상이어야 합니다")
        self._secret = secret.encode()

    def issue(
        self, user_id: UUID, session_id: UUID, issued_at: datetime
    ) -> IssuedSessionTokens:
        return self._issue_pair(
            user_id,
            session_id,
            issued_at,
            issued_at + REFRESH_TOKEN_TTL,
        )

    def rotate(
        self,
        user_id: UUID,
        session_id: UUID,
        issued_at: datetime,
        refresh_token_expires_at: datetime,
    ) -> IssuedSessionTokens:
        return self._issue_pair(
            user_id,
            session_id,
            issued_at,
            refresh_token_expires_at,
        )

    def parse_refresh_token(self, raw_token: str | None) -> RefreshTokenParts | None:
        return parse_refresh_token(raw_token)

    def _issue_pair(
        self,
        user_id: UUID,
        session_id: UUID,
        issued_at: datetime,
        refresh_token_expires_at: datetime,
    ) -> IssuedSessionTokens:
        access_expires_at = issued_at + ACCESS_TOKEN_TTL
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
        refresh_token = f"{session_id}.{secrets.token_urlsafe(48)}"
        return IssuedSessionTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            refresh_token_hash=self._hash_refresh_token(session_id, refresh_token),
            access_token_expires_at=access_expires_at,
            refresh_token_expires_at=refresh_token_expires_at,
        )

    def verify_refresh_token(
        self,
        session_id: UUID,
        refresh_token: str,
        expected_hash: str,
    ) -> bool:
        parts = parse_refresh_token(refresh_token)
        if parts is None or parts.session_id != session_id:
            return False
        candidate_hash = self._hash_refresh_token(session_id, refresh_token)
        return hmac.compare_digest(candidate_hash, expected_hash)

    def _hash_refresh_token(self, session_id: UUID, refresh_token: str) -> str:
        parts = parse_refresh_token(refresh_token)
        if parts is None or parts.session_id != session_id:
            raise ValueError("유효하지 않은 refresh token 형식입니다")
        message = f"refresh:{session_id}:{parts.secret}".encode()
        return hmac.new(self._secret, message, hashlib.sha256).hexdigest()
