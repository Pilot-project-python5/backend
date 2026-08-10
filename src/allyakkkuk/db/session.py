"""동기 SQLAlchemy 엔진과 세션 팩터리."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from allyakkkuk.core.config import get_settings

settings = get_settings()
engine: Engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


def get_db_session() -> Iterator[Session]:
    with SessionFactory() as session:
        yield session
