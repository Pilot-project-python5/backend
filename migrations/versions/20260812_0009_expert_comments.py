"""제품별 전문가 코멘트를 추가한다.

Revision ID: 20260812_0009
Revises: 20260812_0008
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0009"
down_revision: str | None = "20260812_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "expert_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("author_label", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "char_length(btrim(author_label)) BETWEEN 1 AND 100",
            name="ck_expert_comments_author_label_length",
        ),
        sa.CheckConstraint(
            "char_length(btrim(content)) BETWEEN 1 AND 2000",
            name="ck_expert_comments_content_length",
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_expert_comments_sort_order",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_expert_comments_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_expert_comments"),
    )
    op.create_index(
        "ix_expert_comments_product_active_sort",
        "expert_comments",
        ["product_id", "is_active", "sort_order", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_expert_comments_product_active_sort",
        table_name="expert_comments",
    )
    op.drop_table("expert_comments")
