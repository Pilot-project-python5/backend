"""이메일 전달 등록·claim·결과 기록 저장소."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Protocol
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from yeongyangkkuk.auth.models import User
from yeongyangkkuk.care.models import CareItem
from yeongyangkkuk.curation.models import Product
from yeongyangkkuk.notification.models import EmailDelivery, Notification
from yeongyangkkuk.notification.repository import NotificationPersistenceError

EmailDeliveryStatus = Literal["PENDING", "SENDING", "RETRY", "SENT", "FAILED"]


@dataclass(frozen=True, slots=True)
class EmailDeliveryClaim:
    id: UUID
    notification_id: UUID
    recipient_email: str
    notification_type: str
    product_name: str
    reference_date: date
    trigger_days_before: int
    attempt_count: int


class EmailDeliveryRepository(Protocol):
    def enqueue_for_schedule(
        self,
        *,
        scheduled_at: datetime,
        created_at: datetime,
    ) -> int: ...

    def finalize_expired_final_attempts(
        self,
        *,
        now: datetime,
        max_attempts: int,
    ) -> int: ...

    def claim_due(
        self,
        *,
        now: datetime,
        lease_until: datetime,
        max_attempts: int,
    ) -> EmailDeliveryClaim | None: ...

    def mark_sent(
        self,
        *,
        delivery_id: UUID,
        attempt_count: int,
        sent_at: datetime,
    ) -> bool: ...

    def mark_failed(
        self,
        *,
        delivery_id: UUID,
        attempt_count: int,
        failed_at: datetime,
        retry_at: datetime,
        max_attempts: int,
        error_code: str,
    ) -> EmailDeliveryStatus | None: ...


class SQLAlchemyEmailDeliveryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def enqueue_for_schedule(
        self,
        *,
        scheduled_at: datetime,
        created_at: datetime,
    ) -> int:
        try:
            rows = tuple(
                self._session.execute(
                    select(Notification.id, User.email)
                    .join(User, User.id == Notification.user_id)
                    .where(
                        Notification.scheduled_at == scheduled_at,
                        User.status == "ACTIVE",
                        User.email_verified_at.is_not(None),
                    )
                )
            )
            if not rows:
                return 0
            statement = (
                insert(EmailDelivery)
                .values(
                    [
                        {
                            "id": uuid4(),
                            "notification_id": row.id,
                            "recipient_email": row.email,
                            "status": "PENDING",
                            "attempt_count": 0,
                            "next_retry_at": created_at,
                            "sent_at": None,
                            "last_error": None,
                            "created_at": created_at,
                            "updated_at": created_at,
                        }
                        for row in rows
                    ]
                )
                .on_conflict_do_nothing(
                    constraint="uq_email_deliveries_notification_id"
                )
                .returning(EmailDelivery.id)
            )
            created_ids = tuple(self._session.scalars(statement))
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise NotificationPersistenceError from exc
        return len(created_ids)

    def finalize_expired_final_attempts(
        self,
        *,
        now: datetime,
        max_attempts: int,
    ) -> int:
        try:
            finalized_ids = tuple(
                self._session.scalars(
                    update(EmailDelivery)
                    .where(
                        EmailDelivery.status == "SENDING",
                        EmailDelivery.attempt_count >= max_attempts,
                        EmailDelivery.next_retry_at <= now,
                    )
                    .values(
                        status="FAILED",
                        next_retry_at=None,
                        last_error="DELIVERY_RESULT_UNKNOWN",
                        updated_at=now,
                    )
                    .returning(EmailDelivery.id)
                )
            )
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise NotificationPersistenceError from exc
        return len(finalized_ids)

    def claim_due(
        self,
        *,
        now: datetime,
        lease_until: datetime,
        max_attempts: int,
    ) -> EmailDeliveryClaim | None:
        try:
            row = self._session.execute(
                select(EmailDelivery, Notification, Product.name)
                .join(
                    Notification,
                    Notification.id == EmailDelivery.notification_id,
                )
                .join(CareItem, CareItem.id == Notification.care_item_id)
                .join(Product, Product.id == CareItem.product_id)
                .where(
                    EmailDelivery.status.in_(("PENDING", "RETRY", "SENDING")),
                    EmailDelivery.next_retry_at <= now,
                    EmailDelivery.attempt_count < max_attempts,
                )
                .order_by(EmailDelivery.next_retry_at, EmailDelivery.id)
                .with_for_update(of=EmailDelivery, skip_locked=True)
                .limit(1)
            ).one_or_none()
            if row is None:
                self._session.commit()
                return None

            delivery, notification, product_name = row
            delivery.status = "SENDING"
            delivery.attempt_count += 1
            delivery.next_retry_at = lease_until
            delivery.sent_at = None
            delivery.last_error = None
            delivery.updated_at = now
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise NotificationPersistenceError from exc
        return EmailDeliveryClaim(
            id=delivery.id,
            notification_id=notification.id,
            recipient_email=delivery.recipient_email,
            notification_type=notification.notification_type,
            product_name=product_name,
            reference_date=notification.reference_date,
            trigger_days_before=notification.trigger_days_before,
            attempt_count=delivery.attempt_count,
        )

    def mark_sent(
        self,
        *,
        delivery_id: UUID,
        attempt_count: int,
        sent_at: datetime,
    ) -> bool:
        try:
            updated_id = self._session.scalar(
                update(EmailDelivery)
                .where(
                    EmailDelivery.id == delivery_id,
                    EmailDelivery.status == "SENDING",
                    EmailDelivery.attempt_count == attempt_count,
                )
                .values(
                    status="SENT",
                    next_retry_at=None,
                    sent_at=sent_at,
                    last_error=None,
                    updated_at=sent_at,
                )
                .returning(EmailDelivery.id)
            )
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise NotificationPersistenceError from exc
        return updated_id is not None

    def mark_failed(
        self,
        *,
        delivery_id: UUID,
        attempt_count: int,
        failed_at: datetime,
        retry_at: datetime,
        max_attempts: int,
        error_code: str,
    ) -> EmailDeliveryStatus | None:
        next_status: EmailDeliveryStatus = (
            "RETRY" if attempt_count < max_attempts else "FAILED"
        )
        try:
            updated_id = self._session.scalar(
                update(EmailDelivery)
                .where(
                    EmailDelivery.id == delivery_id,
                    EmailDelivery.status == "SENDING",
                    EmailDelivery.attempt_count == attempt_count,
                )
                .values(
                    status=next_status,
                    next_retry_at=retry_at if next_status == "RETRY" else None,
                    sent_at=None,
                    last_error=error_code,
                    updated_at=failed_at,
                )
                .returning(EmailDelivery.id)
            )
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise NotificationPersistenceError from exc
        return next_status if updated_id is not None else None
