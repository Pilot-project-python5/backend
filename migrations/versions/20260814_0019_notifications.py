"""화면과 이메일이 공유하는 논리 알림을 추가한다.

Revision ID: 20260814_0019
Revises: 20260814_0018
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0019"
down_revision: str | None = "20260814_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("care_item_id", sa.Uuid(), nullable=False),
        sa.Column("notification_type", sa.String(length=20), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("trigger_days_before", sa.SmallInteger(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "read_at IS NULL OR read_at >= created_at",
            name="ck_notifications_read_at",
        ),
        sa.CheckConstraint(
            "scheduled_at <= created_at",
            name="ck_notifications_scheduled_at",
        ),
        sa.CheckConstraint(
            "trigger_days_before IN (5, 3, 1)",
            name="ck_notifications_trigger_days",
        ),
        sa.CheckConstraint(
            "notification_type IN ('REPURCHASE', 'EXPIRATION')",
            name="ck_notifications_type",
        ),
        sa.ForeignKeyConstraint(
            ["care_item_id"],
            ["care_items.id"],
            name="fk_notifications_care_item_id_care_items",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notifications_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
        sa.UniqueConstraint(
            "care_item_id",
            "notification_type",
            "reference_date",
            "trigger_days_before",
            name="uq_notifications_logical_event",
        ),
    )
    op.create_index(
        "ix_notifications_user_read_created",
        "notifications",
        ["user_id", "read_at", sa.text("created_at DESC"), "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notifications_user_read_created",
        table_name="notifications",
    )
    op.drop_table("notifications")
