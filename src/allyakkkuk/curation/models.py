"""전문가 큐레이션 카탈로그 SQLAlchemy 모델."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from allyakkkuk.db.base import Base


class ProductCategory(Base):
    __tablename__ = "product_categories"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_product_categories_slug"),
        CheckConstraint(
            "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
            name="ck_product_categories_slug_format",
        ),
        CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 50",
            name="ck_product_categories_name_length",
        ),
        CheckConstraint(
            "sort_order >= 0",
            name="ck_product_categories_sort_order",
        ),
        Index(
            "ix_product_categories_active_sort",
            "is_active",
            "sort_order",
            "slug",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
