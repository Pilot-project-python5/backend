"""회원가입 사용자와 건강 프로필을 추가한다.

Revision ID: 20260810_0002
Revises: 20260810_0001
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0002"
down_revision: str | None = "20260810_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("login_id", sa.String(length=20), nullable=False),
        sa.Column("normalized_login_id", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("normalized_email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(login_id) BETWEEN 5 AND 20",
            name="ck_users_login_id_length",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 50",
            name="ck_users_name_length",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING_EMAIL_VERIFICATION', 'ACTIVE', 'SUSPENDED')",
            name="ck_users_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_email", name="uq_users_normalized_email"),
        sa.UniqueConstraint("normalized_login_id", name="uq_users_normalized_login_id"),
    )
    op.create_table(
        "health_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(length=16), nullable=False),
        sa.Column("height_cm", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("weight_kg", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "gender IN ('MALE', 'FEMALE')", name="ck_health_profiles_gender"
        ),
        sa.CheckConstraint(
            "height_cm >= 50 AND height_cm <= 250",
            name="ck_health_profiles_height_range",
        ),
        sa.CheckConstraint(
            "weight_kg >= 10 AND weight_kg <= 500",
            name="ck_health_profiles_weight_range",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("health_profiles")
    op.drop_table("users")
