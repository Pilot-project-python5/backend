"""제품 카테고리 기준 테이블을 추가한다.

Revision ID: 20260812_0006
Revises: 20260811_0005
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0006"
down_revision: str | None = "20260811_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
            name="ck_product_categories_slug_format",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 50",
            name="ck_product_categories_name_length",
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_product_categories_sort_order",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_product_categories"),
        sa.UniqueConstraint("slug", name="uq_product_categories_slug"),
    )
    op.create_index(
        "ix_product_categories_active_sort",
        "product_categories",
        ["is_active", "sort_order", "slug"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_categories_active_sort",
        table_name="product_categories",
    )
    op.drop_table("product_categories")
