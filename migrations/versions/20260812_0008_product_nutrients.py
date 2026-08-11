"""제품 성분 기준과 단위당 함량 매핑을 추가한다.

Revision ID: 20260812_0008
Revises: 20260812_0007
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0008"
down_revision: str | None = "20260812_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "nutrients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("canonical_unit", sa.String(length=10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "code ~ '^[A-Z0-9]+(_[A-Z0-9]+)*$'",
            name="ck_nutrients_code_format",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 100",
            name="ck_nutrients_name_length",
        ),
        sa.CheckConstraint(
            "canonical_unit IN ('MG', 'G', 'MCG', 'IU')",
            name="ck_nutrients_canonical_unit",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_nutrients"),
        sa.UniqueConstraint("code", name="uq_nutrients_code"),
    )
    op.create_index(
        "ix_nutrients_active_code",
        "nutrients",
        ["is_active", "code"],
        unique=False,
    )
    op.create_table(
        "product_nutrients",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("nutrient_id", sa.Uuid(), nullable=False),
        sa.Column("amount_per_unit", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit", sa.String(length=10), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "amount_per_unit > 0",
            name="ck_product_nutrients_amount_per_unit",
        ),
        sa.CheckConstraint(
            "unit IN ('MG', 'G', 'MCG', 'IU')",
            name="ck_product_nutrients_unit",
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_product_nutrients_sort_order",
        ),
        sa.ForeignKeyConstraint(
            ["nutrient_id"],
            ["nutrients.id"],
            name="fk_product_nutrients_nutrient_id_nutrients",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_product_nutrients_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "product_id",
            "nutrient_id",
            name="pk_product_nutrients",
        ),
    )
    op.create_index(
        "ix_product_nutrients_product_sort",
        "product_nutrients",
        ["product_id", "sort_order", "nutrient_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_nutrients_product_sort",
        table_name="product_nutrients",
    )
    op.drop_table("product_nutrients")
    op.drop_index("ix_nutrients_active_code", table_name="nutrients")
    op.drop_table("nutrients")
