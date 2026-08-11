"""로그인 세션용 access·refresh token 발급과 검증."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

import jwt
from jwt import InvalidTokenError

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


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: UUID
    session_id: UUID
    token_id: UUID
    issued_at: datetime
    expires_at: datetime


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


class AccessTokenVerifier(Protocol):
    def verify_access_token(
        self,
        raw_token: str | None,
        verified_at: datetime,
    ) -> AccessTokenClaims | None: ...


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

    def verify_access_token(
        self,
        raw_token: str | None,
        verified_at: datetime,
    ) -> AccessTokenClaims | None:
        if raw_token is None or not raw_token or verified_at.tzinfo is None:
            return None
        try:
            payload = jwt.decode(
                raw_token,
                self._secret,
                algorithms=["HS256"],
                audience=ACCESS_TOKEN_AUDIENCE,
                issuer=ACCESS_TOKEN_ISSUER,
                options={
                    "require": [
                        "iss",
                        "aud",
                        "sub",
                        "sid",
                        "type",
                        "jti",
                        "iat",
                        "exp",
                    ],
                    "verify_exp": False,
                    "verify_iat": False,
                },
            )
            if payload.get("type") != "access":
                return None
            user_id = _uuid_claim(payload.get("sub"))
            session_id = _uuid_claim(payload.get("sid"))
            token_id = _uuid_claim(payload.get("jti"))
            issued_at = _datetime_claim(payload.get("iat"))
            expires_at = _datetime_claim(payload.get("exp"))
        except (InvalidTokenError, ValueError, TypeError, OverflowError, OSError):
            return None

        if (
            user_id is None
            or session_id is None
            or token_id is None
            or issued_at is None
            or expires_at is None
            or issued_at > verified_at
            or expires_at <= issued_at
            or verified_at >= expires_at
        ):
            return None
        return AccessTokenClaims(
            user_id=user_id,
            session_id=session_id,
            token_id=token_id,
            issued_at=issued_at,
            expires_at=expires_at,
        )

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


def _uuid_claim(value: object) -> UUID | None:
    if not isinstance(value, str):
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _datetime_claim(value: object) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value, tz=UTC)
