"""회원가입에서 확정한 사용자와 건강 프로필 모델."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from allyakkkuk.db.base import Base


class UserStatus(StrEnum):
    PENDING_EMAIL_VERIFICATION = "PENDING_EMAIL_VERIFICATION"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class Gender(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class EmailVerificationPurpose(StrEnum):
    VERIFY_EMAIL = "VERIFY_EMAIL"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("normalized_login_id", name="uq_users_normalized_login_id"),
        UniqueConstraint("normalized_email", name="uq_users_normalized_email"),
        CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 50",
            name="ck_users_name_length",
        ),
        CheckConstraint(
            "char_length(login_id) BETWEEN 5 AND 20",
            name="ck_users_login_id_length",
        ),
        CheckConstraint(
            "status IN ('PENDING_EMAIL_VERIFICATION', 'ACTIVE', 'SUSPENDED')",
            name="ck_users_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    login_id: Mapped[str] = mapped_column(String(20), nullable=False)
    normalized_login_id: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    normalized_email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class HealthProfile(Base):
    __tablename__ = "health_profiles"
    __table_args__ = (
        CheckConstraint(
            "gender IN ('MALE', 'FEMALE')", name="ck_health_profiles_gender"
        ),
        CheckConstraint(
            "height_cm >= 50 AND height_cm <= 250",
            name="ck_health_profiles_height_range",
        ),
        CheckConstraint(
            "weight_kg >= 10 AND weight_kg <= 500",
            name="ck_health_profiles_weight_range",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(16), nullable=False)
    height_cm: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class EmailVerification(Base):
    __tablename__ = "email_verifications"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('VERIFY_EMAIL')",
            name="ck_email_verifications_purpose",
        ),
        CheckConstraint(
            "failed_attempts BETWEEN 0 AND 5",
            name="ck_email_verifications_failed_attempts",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_email_verifications_expires_at",
        ),
        CheckConstraint(
            "resend_available_at > created_at",
            name="ck_email_verifications_resend_available_at",
        ),
        CheckConstraint(
            "used_at IS NULL OR used_at >= created_at",
            name="ck_email_verifications_used_at",
        ),
        CheckConstraint(
            "superseded_at IS NULL OR superseded_at >= created_at",
            name="ck_email_verifications_superseded_at",
        ),
        CheckConstraint(
            "NOT (used_at IS NOT NULL AND superseded_at IS NOT NULL)",
            name="ck_email_verifications_terminal_state",
        ),
        Index(
            "ix_email_verifications_user_created_at",
            "user_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resend_available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    failed_attempts: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
