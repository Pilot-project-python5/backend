"""비밀번호 해시 포트와 Argon2id 로컬 구현."""

from __future__ import annotations

from typing import Protocol

from argon2 import PasswordHasher as Argon2Engine
from argon2.exceptions import InvalidHashError, VerificationError


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, encoded: str) -> bool: ...


class Argon2PasswordHasher:
    def __init__(self, engine: Argon2Engine | None = None) -> None:
        self._engine = engine or Argon2Engine()

    def hash(self, password: str) -> str:
        return self._engine.hash(password)

    def verify(self, password: str, encoded: str) -> bool:
        try:
            return self._engine.verify(encoded, password)
        except (InvalidHashError, VerificationError):
            return False
