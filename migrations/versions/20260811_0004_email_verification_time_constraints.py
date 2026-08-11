"""이메일 인증 완료·대체 시각 무결성 제약을 추가한다.

Revision ID: 20260811_0004
Revises: 20260811_0003
Create Date: 2026-08-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260811_0004"
down_revision: str | None = "20260811_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_email_verifications_used_at",
        "email_verifications",
        "used_at IS NULL OR used_at >= created_at",
    )
    op.create_check_constraint(
        "ck_email_verifications_superseded_at",
        "email_verifications",
        "superseded_at IS NULL OR superseded_at >= created_at",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_email_verifications_superseded_at",
        "email_verifications",
        type_="check",
    )
    op.drop_constraint(
        "ck_email_verifications_used_at",
        "email_verifications",
        type_="check",
    )
