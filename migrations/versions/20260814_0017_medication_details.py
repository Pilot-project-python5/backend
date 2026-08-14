"""의약품 상세 카탈로그를 추가한다.

Revision ID: 20260814_0017
Revises: 20260814_0016
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0017"
down_revision: str | None = "20260814_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "medication_details",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("permit_code", sa.String(length=50), nullable=False),
        sa.Column("classification", sa.String(length=20), nullable=False),
        sa.Column("active_ingredients", sa.Text(), nullable=False),
        sa.Column("efficacy", sa.Text(), nullable=False),
        sa.Column("dosage_instructions", sa.Text(), nullable=False),
        sa.Column("precautions", sa.Text(), nullable=False),
        sa.Column("storage_instructions", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_reviewed_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(btrim(active_ingredients)) BETWEEN 1 AND 1000",
            name="ck_medication_details_active_ingredients_length",
        ),
        sa.CheckConstraint(
            "classification IN ('OTC', 'PRESCRIPTION')",
            name="ck_medication_details_classification",
        ),
        sa.CheckConstraint(
            "char_length(btrim(dosage_instructions)) BETWEEN 1 AND 4000",
            name="ck_medication_details_dosage_length",
        ),
        sa.CheckConstraint(
            "char_length(btrim(efficacy)) BETWEEN 1 AND 4000",
            name="ck_medication_details_efficacy_length",
        ),
        sa.CheckConstraint(
            "permit_code ~ '^[A-Z0-9]+(-[A-Z0-9]+)*$'",
            name="ck_medication_details_permit_code_format",
        ),
        sa.CheckConstraint(
            "char_length(btrim(precautions)) BETWEEN 1 AND 4000",
            name="ck_medication_details_precautions_length",
        ),
        sa.CheckConstraint(
            "char_length(btrim(source_name)) BETWEEN 1 AND 200",
            name="ck_medication_details_source_name_length",
        ),
        sa.CheckConstraint(
            "char_length(source_url) BETWEEN 9 AND 2048",
            name="ck_medication_details_source_url_length",
        ),
        sa.CheckConstraint(
            "source_url ~ '^https://[^[:space:]#]+$'",
            name="ck_medication_details_source_url_https",
        ),
        sa.CheckConstraint(
            "source_url !~ '^https://[^/]*@'",
            name="ck_medication_details_source_url_no_userinfo",
        ),
        sa.CheckConstraint(
            "char_length(btrim(storage_instructions)) BETWEEN 1 AND 1000",
            name="ck_medication_details_storage_length",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_medication_details_updated_at",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_medication_details_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("product_id", name="pk_medication_details"),
        sa.UniqueConstraint("permit_code", name="uq_medication_details_permit_code"),
    )
    op.create_index(
        "ix_medication_details_classification_product",
        "medication_details",
        ["classification", "product_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_medication_details_classification_product",
        table_name="medication_details",
    )
    op.drop_table("medication_details")
