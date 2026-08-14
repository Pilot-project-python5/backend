"""복용 항목 구매분별 유통기한을 추가한다.

Revision ID: 20260814_0018
Revises: 20260814_0017
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0018"
down_revision: str | None = "20260814_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "care_items",
        sa.Column("expiration_date", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_care_items_expiration_user",
        "care_items",
        ["expiration_date", "user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_care_items_expiration_user", table_name="care_items")
    op.drop_column("care_items", "expiration_date")
