"""모든 기능 모델이 공유하는 SQLAlchemy 메타데이터."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
