"""논리 알림별 이메일 전달 상태를 추가한다.

Revision ID: 20260814_0020
Revises: 20260814_0019
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0020"
down_revision: str | None = "20260814_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_email", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempt_count", sa.SmallInteger(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "attempt_count BETWEEN 0 AND 3",
            name="ck_email_deliveries_attempt_count",
        ),
        sa.CheckConstraint(
            "last_error IS NULL OR last_error IN "
            "('SMTP_DELIVERY_FAILED', 'DELIVERY_RESULT_UNKNOWN')",
            name="ck_email_deliveries_last_error",
        ),
        sa.CheckConstraint(
            "sent_at IS NULL OR sent_at >= created_at",
            name="ck_email_deliveries_sent_at",
        ),
        sa.CheckConstraint(
            "(status = 'PENDING' AND attempt_count = 0 "
            "AND next_retry_at IS NOT NULL AND sent_at IS NULL "
            "AND last_error IS NULL) OR "
            "(status = 'SENDING' AND attempt_count BETWEEN 1 AND 3 "
            "AND next_retry_at IS NOT NULL AND sent_at IS NULL "
            "AND last_error IS NULL) OR "
            "(status = 'RETRY' AND attempt_count BETWEEN 1 AND 2 "
            "AND next_retry_at IS NOT NULL AND sent_at IS NULL "
            "AND last_error = 'SMTP_DELIVERY_FAILED') OR "
            "(status = 'SENT' AND attempt_count BETWEEN 1 AND 3 "
            "AND next_retry_at IS NULL AND sent_at IS NOT NULL "
            "AND last_error IS NULL) OR "
            "(status = 'FAILED' AND attempt_count = 3 "
            "AND next_retry_at IS NULL AND sent_at IS NULL "
            "AND last_error IN "
            "('SMTP_DELIVERY_FAILED', 'DELIVERY_RESULT_UNKNOWN'))",
            name="ck_email_deliveries_state",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'SENDING', 'RETRY', 'SENT', 'FAILED')",
            name="ck_email_deliveries_status",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_email_deliveries_updated_at",
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            name="fk_email_deliveries_notification_id_notifications",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_email_deliveries"),
        sa.UniqueConstraint(
            "notification_id",
            name="uq_email_deliveries_notification_id",
        ),
    )
    op.create_index(
        "ix_email_deliveries_due",
        "email_deliveries",
        ["next_retry_at", "id"],
        postgresql_where=sa.text("status IN ('PENDING', 'SENDING', 'RETRY')"),
    )


def downgrade() -> None:
    op.drop_index("ix_email_deliveries_due", table_name="email_deliveries")
    op.drop_table("email_deliveries")
