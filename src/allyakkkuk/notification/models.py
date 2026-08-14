"""논리 알림 SQLAlchemy 모델."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from allyakkkuk.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "notification_type IN ('REPURCHASE', 'EXPIRATION')",
            name="ck_notifications_type",
        ),
        CheckConstraint(
            "trigger_days_before IN (5, 3, 1)",
            name="ck_notifications_trigger_days",
        ),
        CheckConstraint(
            "scheduled_at <= created_at",
            name="ck_notifications_scheduled_at",
        ),
        CheckConstraint(
            "read_at IS NULL OR read_at >= created_at",
            name="ck_notifications_read_at",
        ),
        UniqueConstraint(
            "care_item_id",
            "notification_type",
            "reference_date",
            "trigger_days_before",
            name="uq_notifications_logical_event",
        ),
        Index(
            "ix_notifications_user_read_created",
            "user_id",
            "read_at",
            text("created_at DESC"),
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    care_item_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("care_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    notification_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    trigger_days_before: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
