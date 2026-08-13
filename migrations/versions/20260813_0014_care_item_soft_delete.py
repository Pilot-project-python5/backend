"""복용 제품의 이력 보존형 소프트 삭제를 추가한다.

Revision ID: 20260813_0014
Revises: 20260812_0013
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0014"
down_revision: str | None = "20260812_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "care_items",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_care_items_deleted_at",
        "care_items",
        "deleted_at IS NULL OR deleted_at >= created_at",
    )
    op.create_index(
        "ix_care_items_active_user_created_at",
        "care_items",
        ["user_id", "created_at", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_care_items_active_user_created_at",
        table_name="care_items",
    )
    op.drop_constraint(
        "ck_care_items_deleted_at",
        "care_items",
        type_="check",
    )
    op.drop_column("care_items", "deleted_at")
