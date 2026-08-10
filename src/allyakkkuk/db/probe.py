"""데이터베이스 준비 상태 포트와 PostgreSQL 구현."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import Engine, text


class DatabaseProbe(Protocol):
    def check(self) -> None: ...


class SQLAlchemyDatabaseProbe:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def check(self) -> None:
        with self._engine.connect() as connection:
            connection.execute(text("SELECT 1"))
