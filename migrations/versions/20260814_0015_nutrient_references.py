"""버전 관리 영양소 섭취기준 테이블을 추가한다.

Revision ID: 20260814_0015
Revises: 20260813_0014
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0015"
down_revision: str | None = "20260813_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "nutrient_reference_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("published_on", sa.Date(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version", name="uq_nutrient_reference_versions_version"),
        sa.UniqueConstraint("checksum", name="uq_nutrient_reference_versions_checksum"),
        sa.CheckConstraint(
            "char_length(btrim(source_name)) BETWEEN 1 AND 200",
            name="ck_nutrient_reference_versions_source_name",
        ),
        sa.CheckConstraint(
            "source_url LIKE 'https://%'",
            name="ck_nutrient_reference_versions_source_url",
        ),
        sa.CheckConstraint(
            "char_length(checksum) = 64", name="ck_nutrient_reference_versions_checksum"
        ),
    )
    op.create_table(
        "nutrient_reference_values",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("nutrient_id", sa.Uuid(), nullable=False),
        sa.Column("gender", sa.String(16), nullable=False),
        sa.Column("age_min", sa.SmallInteger(), nullable=False),
        sa.Column("age_max", sa.SmallInteger(), nullable=False),
        sa.Column("reference_type", sa.String(8), nullable=False),
        sa.Column("reference_amount", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit", sa.String(10), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["version_id"], ["nutrient_reference_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["nutrient_id"], ["nutrients.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "version_id",
            "nutrient_id",
            "gender",
            "age_min",
            "age_max",
            "reference_type",
            name="uq_nutrient_reference_values_range",
        ),
        sa.CheckConstraint(
            "gender IN ('MALE', 'FEMALE')", name="ck_nutrient_reference_values_gender"
        ),
        sa.CheckConstraint(
            "age_min BETWEEN 0 AND 120 AND age_max BETWEEN age_min AND 120",
            name="ck_nutrient_reference_values_age_range",
        ),
        sa.CheckConstraint(
            "reference_type IN ('RNI', 'AI')", name="ck_nutrient_reference_values_type"
        ),
        sa.CheckConstraint(
            "reference_amount > 0", name="ck_nutrient_reference_values_amount"
        ),
        sa.CheckConstraint(
            "unit IN ('MG', 'G', 'MCG', 'IU')", name="ck_nutrient_reference_values_unit"
        ),
    )
    op.create_index(
        "ix_nutrient_reference_values_lookup",
        "nutrient_reference_values",
        ["version_id", "gender", "age_min", "age_max", "nutrient_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_nutrient_reference_values_lookup", table_name="nutrient_reference_values"
    )
    op.drop_table("nutrient_reference_values")
    op.drop_table("nutrient_reference_versions")
