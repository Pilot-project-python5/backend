"""의약품 카탈로그 상세 SQLAlchemy 모델."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from allyakkkuk.db.base import Base


class MedicationDetail(Base):
    __tablename__ = "medication_details"
    __table_args__ = (
        UniqueConstraint("permit_code", name="uq_medication_details_permit_code"),
        CheckConstraint(
            "permit_code ~ '^[A-Z0-9]+(-[A-Z0-9]+)*$'",
            name="ck_medication_details_permit_code_format",
        ),
        CheckConstraint(
            "classification IN ('OTC', 'PRESCRIPTION')",
            name="ck_medication_details_classification",
        ),
        CheckConstraint(
            "char_length(btrim(active_ingredients)) BETWEEN 1 AND 1000",
            name="ck_medication_details_active_ingredients_length",
        ),
        CheckConstraint(
            "char_length(btrim(efficacy)) BETWEEN 1 AND 4000",
            name="ck_medication_details_efficacy_length",
        ),
        CheckConstraint(
            "char_length(btrim(dosage_instructions)) BETWEEN 1 AND 4000",
            name="ck_medication_details_dosage_length",
        ),
        CheckConstraint(
            "char_length(btrim(precautions)) BETWEEN 1 AND 4000",
            name="ck_medication_details_precautions_length",
        ),
        CheckConstraint(
            "char_length(btrim(storage_instructions)) BETWEEN 1 AND 1000",
            name="ck_medication_details_storage_length",
        ),
        CheckConstraint(
            "char_length(btrim(source_name)) BETWEEN 1 AND 200",
            name="ck_medication_details_source_name_length",
        ),
        CheckConstraint(
            "char_length(source_url) BETWEEN 9 AND 2048",
            name="ck_medication_details_source_url_length",
        ),
        CheckConstraint(
            "source_url ~ '^https://[^[:space:]#]+$'",
            name="ck_medication_details_source_url_https",
        ),
        CheckConstraint(
            "source_url !~ '^https://[^/]*@'",
            name="ck_medication_details_source_url_no_userinfo",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_medication_details_updated_at",
        ),
        Index(
            "ix_medication_details_classification_product",
            "classification",
            "product_id",
        ),
    )

    product_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permit_code: Mapped[str] = mapped_column(String(50), nullable=False)
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    active_ingredients: Mapped[str] = mapped_column(Text, nullable=False)
    efficacy: Mapped[str] = mapped_column(Text, nullable=False)
    dosage_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    precautions: Mapped[str] = mapped_column(Text, nullable=False)
    storage_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_reviewed_on: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
