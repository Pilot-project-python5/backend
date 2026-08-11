"""게시 추천 제품과 카테고리 매핑을 추가한다.

Revision ID: 20260812_0007
Revises: 20260812_0006
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0007"
down_revision: str | None = "20260812_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=50), nullable=False),
        sa.Column("product_type", sa.String(length=20), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("unit_form", sa.String(length=20), nullable=False),
        sa.Column("units_per_package", sa.Numeric(10, 2), nullable=False),
        sa.Column("display_price", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "sku ~ '^[A-Z0-9]+(-[A-Z0-9]+)*$'",
            name="ck_products_sku_format",
        ),
        sa.CheckConstraint(
            "product_type IN ('SUPPLEMENT', 'MEDICATION')",
            name="ck_products_product_type",
        ),
        sa.CheckConstraint(
            "char_length(btrim(brand)) BETWEEN 1 AND 100",
            name="ck_products_brand_length",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 200",
            name="ck_products_name_length",
        ),
        sa.CheckConstraint(
            "char_length(btrim(image_url)) BETWEEN 1 AND 2048",
            name="ck_products_image_url_length",
        ),
        sa.CheckConstraint(
            "unit_form IN ('TABLET', 'CAPSULE', 'SCOOP', 'PACKET')",
            name="ck_products_unit_form",
        ),
        sa.CheckConstraint(
            "units_per_package > 0",
            name="ck_products_units_per_package",
        ),
        sa.CheckConstraint(
            "display_price >= 0",
            name="ck_products_display_price",
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_products_sort_order",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_products_updated_at",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.UniqueConstraint("sku", name="uq_products_sku"),
    )
    op.create_index(
        "ix_products_published_sort",
        "products",
        ["is_published", "sort_order", "sku"],
        unique=False,
    )
    op.create_table(
        "product_category_mappings",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["product_categories.id"],
            name="fk_product_category_mappings_category_id_product_categories",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_product_category_mappings_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "product_id",
            "category_id",
            name="pk_product_category_mappings",
        ),
    )
    op.create_index(
        "ix_product_category_mappings_category_product",
        "product_category_mappings",
        ["category_id", "product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_category_mappings_category_product",
        table_name="product_category_mappings",
    )
    op.drop_table("product_category_mappings")
    op.drop_index("ix_products_published_sort", table_name="products")
    op.drop_table("products")
