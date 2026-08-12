"""제품별 외부 구매 링크를 추가한다.

Revision ID: 20260812_0010
Revises: 20260812_0009
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0010"
down_revision: str | None = "20260812_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "purchase_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("provider_name", sa.String(length=100), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "char_length(btrim(provider_name)) BETWEEN 1 AND 100",
            name="ck_purchase_links_provider_name_length",
        ),
        sa.CheckConstraint(
            "char_length(url) BETWEEN 9 AND 2048",
            name="ck_purchase_links_url_length",
        ),
        sa.CheckConstraint(
            "url ~ '^https://[^[:space:]#]+$'",
            name="ck_purchase_links_url_https",
        ),
        sa.CheckConstraint(
            "url !~ '^https://[^/]*@'",
            name="ck_purchase_links_url_no_userinfo",
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_purchase_links_sort_order",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_purchase_links_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_purchase_links"),
    )
    op.create_index(
        "ix_purchase_links_product_active_sort",
        "purchase_links",
        ["product_id", "is_active", "sort_order", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_purchase_links_product_active_sort",
        table_name="purchase_links",
    )
    op.drop_table("purchase_links")
