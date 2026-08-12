"""복용 제품 구매 수량의 등록 시점 단위를 추가한다.

Revision ID: 20260812_0013
Revises: 20260812_0012
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0013"
down_revision: str | None = "20260812_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "care_items",
        sa.Column("quantity_unit", sa.String(length=20), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE care_items AS ci
            SET quantity_unit = p.unit_form
            FROM products AS p
            WHERE p.id = ci.product_id
            """
        )
    )
    op.create_check_constraint(
        "ck_care_items_quantity_unit",
        "care_items",
        "quantity_unit IN ('TABLET', 'CAPSULE', 'SCOOP', 'PACKET')",
    )
    op.alter_column(
        "care_items",
        "quantity_unit",
        existing_type=sa.String(length=20),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_care_items_quantity_unit",
        "care_items",
        type_="check",
    )
    op.drop_column("care_items", "quantity_unit")
