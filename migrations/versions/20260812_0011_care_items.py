"""사용자 복용 제품 등록 테이블을 추가한다.

Revision ID: 20260812_0011
Revises: 20260812_0010
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0011"
down_revision: str | None = "20260812_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "care_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("intake_start_date", sa.Date(), nullable=False),
        sa.Column("total_quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("dose_per_intake", sa.Numeric(12, 3), nullable=False),
        sa.Column("intakes_per_day", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "intake_start_date >= purchase_date",
            name="ck_care_items_date_order",
        ),
        sa.CheckConstraint(
            "total_quantity > 0 AND total_quantity <= 999999999.999",
            name="ck_care_items_total_quantity",
        ),
        sa.CheckConstraint(
            "dose_per_intake > 0 AND dose_per_intake <= 999999999.999",
            name="ck_care_items_dose_per_intake",
        ),
        sa.CheckConstraint(
            "dose_per_intake <= total_quantity",
            name="ck_care_items_dose_within_total",
        ),
        sa.CheckConstraint(
            "intakes_per_day BETWEEN 1 AND 24",
            name="ck_care_items_intakes_per_day",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_care_items_updated_at",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_care_items_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_care_items_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_care_items"),
    )
    op.create_index(
        "ix_care_items_product_id",
        "care_items",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_care_items_user_created_at",
        "care_items",
        ["user_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_care_items_user_created_at", table_name="care_items")
    op.drop_index("ix_care_items_product_id", table_name="care_items")
    op.drop_table("care_items")
