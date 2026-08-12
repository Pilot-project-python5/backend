"""사용자 복용 제품 SQLAlchemy 모델."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from allyakkkuk.db.base import Base


class CareItem(Base):
    __tablename__ = "care_items"
    __table_args__ = (
        CheckConstraint(
            "intake_start_date >= purchase_date",
            name="ck_care_items_date_order",
        ),
        CheckConstraint(
            "total_quantity > 0 AND total_quantity <= 999999999.999",
            name="ck_care_items_total_quantity",
        ),
        CheckConstraint(
            "dose_per_intake > 0 AND dose_per_intake <= 999999999.999",
            name="ck_care_items_dose_per_intake",
        ),
        CheckConstraint(
            "dose_per_intake <= total_quantity",
            name="ck_care_items_dose_within_total",
        ),
        CheckConstraint(
            "intakes_per_day BETWEEN 1 AND 24",
            name="ck_care_items_intakes_per_day",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_care_items_updated_at",
        ),
        Index(
            "ix_care_items_user_created_at",
            "user_id",
            "created_at",
            "id",
        ),
        Index("ix_care_items_product_id", "product_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    intake_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    dose_per_intake: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    intakes_per_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
