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


class EmailDelivery(Base):
    __tablename__ = "email_deliveries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'SENDING', 'RETRY', 'SENT', 'FAILED')",
            name="ck_email_deliveries_status",
        ),
        CheckConstraint(
            "attempt_count BETWEEN 0 AND 3",
            name="ck_email_deliveries_attempt_count",
        ),
        CheckConstraint(
            "last_error IS NULL OR last_error IN "
            "('SMTP_DELIVERY_FAILED', 'DELIVERY_RESULT_UNKNOWN')",
            name="ck_email_deliveries_last_error",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_email_deliveries_updated_at",
        ),
        CheckConstraint(
            "sent_at IS NULL OR sent_at >= created_at",
            name="ck_email_deliveries_sent_at",
        ),
        CheckConstraint(
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
        Index(
            "ix_email_deliveries_due",
            "next_retry_at",
            "id",
            postgresql_where=text("status IN ('PENDING', 'SENDING', 'RETRY')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    notification_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    attempt_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
