"""버전 관리 영양소 섭취기준 SQLAlchemy 모델."""

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
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from yeongyangkkuk.db.base import Base


class NutrientReferenceVersion(Base):
    __tablename__ = "nutrient_reference_versions"
    __table_args__ = (
        UniqueConstraint("version", name="uq_nutrient_reference_versions_version"),
        UniqueConstraint("checksum", name="uq_nutrient_reference_versions_checksum"),
        CheckConstraint(
            "char_length(btrim(source_name)) BETWEEN 1 AND 200",
            name="ck_nutrient_reference_versions_source_name",
        ),
        CheckConstraint(
            "source_url LIKE 'https://%'",
            name="ck_nutrient_reference_versions_source_url",
        ),
        CheckConstraint(
            "char_length(checksum) = 64", name="ck_nutrient_reference_versions_checksum"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    published_on: Mapped[date] = mapped_column(Date, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NutrientReferenceValue(Base):
    __tablename__ = "nutrient_reference_values"
    __table_args__ = (
        UniqueConstraint(
            "version_id",
            "nutrient_id",
            "gender",
            "age_min",
            "age_max",
            "reference_type",
            name="uq_nutrient_reference_values_range",
        ),
        CheckConstraint(
            "gender IN ('MALE', 'FEMALE')", name="ck_nutrient_reference_values_gender"
        ),
        CheckConstraint(
            "age_min BETWEEN 0 AND 120 AND age_max BETWEEN age_min AND 120",
            name="ck_nutrient_reference_values_age_range",
        ),
        CheckConstraint(
            "reference_type IN ('RNI', 'AI')", name="ck_nutrient_reference_values_type"
        ),
        CheckConstraint(
            "reference_amount > 0", name="ck_nutrient_reference_values_amount"
        ),
        CheckConstraint(
            "unit IN ('MG', 'G', 'MCG', 'IU')", name="ck_nutrient_reference_values_unit"
        ),
        Index(
            "ix_nutrient_reference_values_lookup",
            "version_id",
            "gender",
            "age_min",
            "age_max",
            "nutrient_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("nutrient_reference_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    nutrient_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("nutrients.id", ondelete="RESTRICT"), nullable=False
    )
    gender: Mapped[str] = mapped_column(String(16), nullable=False)
    age_min: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    age_max: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reference_type: Mapped[str] = mapped_column(String(8), nullable=False)
    reference_amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(10), nullable=False)
