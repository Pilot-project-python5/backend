"""이메일 인증번호 생성과 서버 비밀값 기반 검증."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Protocol
from uuid import UUID


class VerificationCodeGenerator(Protocol):
    def generate(self) -> str: ...


class VerificationCodeHasher(Protocol):
    def hash(self, verification_id: UUID, code: str) -> str: ...

    def verify(self, verification_id: UUID, code: str, code_hash: str) -> bool: ...


class SecureVerificationCodeGenerator:
    def generate(self) -> str:
        return f"{secrets.randbelow(1_000_000):06d}"


class HmacVerificationCodeHasher:
    def __init__(self, secret: str) -> None:
        if not secret:
            raise ValueError("이메일 인증 HMAC 비밀값이 필요합니다")
        self._secret = secret.encode("utf-8")

    def hash(self, verification_id: UUID, code: str) -> str:
        message = f"{verification_id}:{code}".encode()
        return hmac.new(self._secret, message, hashlib.sha256).hexdigest()

    def verify(self, verification_id: UUID, code: str, code_hash: str) -> bool:
        expected = self.hash(verification_id, code)
        return hmac.compare_digest(expected, code_hash)
