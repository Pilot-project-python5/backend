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
    String,
    UniqueConstraint,
    Uuid,
    text,
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
            "quantity_unit IN ('TABLET', 'CAPSULE', 'SCOOP', 'PACKET')",
            name="ck_care_items_quantity_unit",
        ),
        CheckConstraint(
            "intakes_per_day BETWEEN 1 AND 24",
            name="ck_care_items_intakes_per_day",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_care_items_updated_at",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_at >= created_at",
            name="ck_care_items_deleted_at",
        ),
        Index(
            "ix_care_items_user_created_at",
            "user_id",
            "created_at",
            "id",
        ),
        Index("ix_care_items_product_id", "product_id"),
        Index(
            "ix_care_items_active_user_created_at",
            "user_id",
            "created_at",
            "id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
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
    quantity_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    dose_per_intake: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    intakes_per_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


class CareNutrientSnapshot(Base):
    """복용 제품 등록 시점의 영양 성분 값."""

    __tablename__ = "care_nutrient_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "care_item_id",
            "nutrient_id",
            name="uq_care_nutrient_snapshots_item_nutrient",
        ),
        CheckConstraint(
            "char_length(btrim(nutrient_name)) BETWEEN 1 AND 100",
            name="ck_care_nutrient_snapshots_name_length",
        ),
        CheckConstraint(
            "amount_per_unit > 0",
            name="ck_care_nutrient_snapshots_amount",
        ),
        CheckConstraint(
            "unit IN ('MG', 'G', 'MCG', 'IU')",
            name="ck_care_nutrient_snapshots_unit",
        ),
        Index("ix_care_nutrient_snapshots_nutrient_id", "nutrient_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    care_item_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("care_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    nutrient_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("nutrients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    nutrient_name: Mapped[str] = mapped_column(String(100), nullable=False)
    amount_per_unit: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(10), nullable=False)
