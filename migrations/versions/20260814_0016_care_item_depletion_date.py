"""복용 항목 예상 소진일을 추가하고 기존 계획을 백필한다.

Revision ID: 20260814_0016
Revises: 20260814_0015
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0016"
down_revision: str | None = "20260814_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "care_items",
        sa.Column("expected_depletion_date", sa.Date(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE care_items
            SET expected_depletion_date = intake_start_date
                + (CEIL(total_quantity / (dose_per_intake * intakes_per_day))::integer - 1)
            """
        )
    )
    op.create_check_constraint(
        "ck_care_items_depletion_date_order",
        "care_items",
        "expected_depletion_date >= intake_start_date",
    )
    op.alter_column("care_items", "expected_depletion_date", nullable=False)
    op.create_index(
        "ix_care_items_depletion_user",
        "care_items",
        ["expected_depletion_date", "user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_care_items_depletion_user", table_name="care_items")
    op.drop_constraint(
        "ck_care_items_depletion_date_order", "care_items", type_="check"
    )
    op.drop_column("care_items", "expected_depletion_date")
