"""이메일 인증번호 발급 이력 테이블을 추가한다.

Revision ID: 20260811_0003
Revises: 20260810_0002
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0003"
down_revision: str | None = "20260810_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resend_available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "failed_attempts", sa.SmallInteger(), nullable=False, server_default="0"
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_email_verifications_expires_at",
        ),
        sa.CheckConstraint(
            "failed_attempts BETWEEN 0 AND 5",
            name="ck_email_verifications_failed_attempts",
        ),
        sa.CheckConstraint(
            "purpose IN ('VERIFY_EMAIL')",
            name="ck_email_verifications_purpose",
        ),
        sa.CheckConstraint(
            "resend_available_at > created_at",
            name="ck_email_verifications_resend_available_at",
        ),
        sa.CheckConstraint(
            "NOT (used_at IS NOT NULL AND superseded_at IS NOT NULL)",
            name="ck_email_verifications_terminal_state",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_verifications_user_created_at",
        "email_verifications",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_email_verifications_user_created_at",
        table_name="email_verifications",
    )
    op.drop_table("email_verifications")
