"""논리 알림 생성·조회·읽음 저장소 포트와 PostgreSQL 구현."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.care.models import CareItem
from allyakkkuk.curation.models import Product
from allyakkkuk.notification.models import Notification


class NotificationPersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class NotificationTrigger:
    days_before: int
    reference_date: date


RepurchaseTrigger = NotificationTrigger


class RepurchaseNotificationRepository(Protocol):
    def create_repurchase_notifications(
        self,
        *,
        triggers: tuple[RepurchaseTrigger, ...],
        scheduled_at: datetime,
        created_at: datetime,
    ) -> int: ...


class ExpirationNotificationRepository(Protocol):
    def create_expiration_notifications(
        self,
        *,
        triggers: tuple[NotificationTrigger, ...],
        scheduled_at: datetime,
        created_at: datetime,
    ) -> int: ...


@dataclass(frozen=True, slots=True)
class NotificationListRecord:
    id: UUID
    care_item_id: UUID
    product_name: str
    notification_type: str
    reference_date: date
    trigger_days_before: int
    scheduled_at: datetime
    created_at: datetime
    read_at: datetime | None


@dataclass(frozen=True, slots=True)
class NotificationPageRecord:
    items: tuple[NotificationListRecord, ...]
    total: int


@dataclass(frozen=True, slots=True)
class NotificationReadRecord:
    id: UUID
    read_at: datetime


class NotificationRepository(Protocol):
    def list_for_user(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
    ) -> NotificationPageRecord: ...

    def mark_read(
        self,
        *,
        user_id: UUID,
        notification_id: UUID,
        read_at: datetime,
    ) -> NotificationReadRecord | None: ...


class SQLAlchemyRepurchaseNotificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_repurchase_notifications(
        self,
        *,
        triggers: tuple[RepurchaseTrigger, ...],
        scheduled_at: datetime,
        created_at: datetime,
    ) -> int:
        trigger_by_date = {
            trigger.reference_date: trigger.days_before for trigger in triggers
        }
        try:
            rows = tuple(
                self._session.execute(
                    select(
                        CareItem.id,
                        CareItem.user_id,
                        CareItem.expected_depletion_date,
                    ).where(
                        CareItem.deleted_at.is_(None),
                        CareItem.expected_depletion_date.in_(trigger_by_date),
                    )
                )
            )
            if not rows:
                return 0

            statement = (
                insert(Notification)
                .values(
                    [
                        {
                            "user_id": row.user_id,
                            "care_item_id": row.id,
                            "notification_type": "REPURCHASE",
                            "reference_date": row.expected_depletion_date,
                            "trigger_days_before": trigger_by_date[
                                row.expected_depletion_date
                            ],
                            "scheduled_at": scheduled_at,
                            "created_at": created_at,
                            "read_at": None,
                        }
                        for row in rows
                    ]
                )
                .on_conflict_do_nothing(constraint="uq_notifications_logical_event")
                .returning(Notification.id)
            )
            created_ids = tuple(self._session.scalars(statement))
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise NotificationPersistenceError from exc
        return len(created_ids)


class SQLAlchemyExpirationNotificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_expiration_notifications(
        self,
        *,
        triggers: tuple[NotificationTrigger, ...],
        scheduled_at: datetime,
        created_at: datetime,
    ) -> int:
        trigger_by_date = {
            trigger.reference_date: trigger.days_before for trigger in triggers
        }
        try:
            rows = tuple(
                self._session.execute(
                    select(
                        CareItem.id,
                        CareItem.user_id,
                        CareItem.expiration_date,
                    ).where(
                        CareItem.deleted_at.is_(None),
                        CareItem.expiration_date.in_(trigger_by_date),
                    )
                )
            )
            if not rows:
                return 0

            statement = (
                insert(Notification)
                .values(
                    [
                        {
                            "user_id": row.user_id,
                            "care_item_id": row.id,
                            "notification_type": "EXPIRATION",
                            "reference_date": cast(date, row.expiration_date),
                            "trigger_days_before": trigger_by_date[
                                cast(date, row.expiration_date)
                            ],
                            "scheduled_at": scheduled_at,
                            "created_at": created_at,
                            "read_at": None,
                        }
                        for row in rows
                    ]
                )
                .on_conflict_do_nothing(constraint="uq_notifications_logical_event")
                .returning(Notification.id)
            )
            created_ids = tuple(self._session.scalars(statement))
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise NotificationPersistenceError from exc
        return len(created_ids)


class SQLAlchemyNotificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_user(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
    ) -> NotificationPageRecord:
        try:
            total = int(
                self._session.scalar(
                    select(func.count())
                    .select_from(Notification)
                    .where(Notification.user_id == user_id)
                )
                or 0
            )
            offset = (page - 1) * page_size
            if offset >= total:
                return NotificationPageRecord(items=(), total=total)

            rows = self._session.execute(
                select(Notification, Product.name)
                .join(CareItem, CareItem.id == Notification.care_item_id)
                .join(Product, Product.id == CareItem.product_id)
                .where(Notification.user_id == user_id)
                .order_by(Notification.created_at.desc(), Notification.id.desc())
                .offset(offset)
                .limit(page_size)
            )
            items = tuple(
                NotificationListRecord(
                    id=notification.id,
                    care_item_id=notification.care_item_id,
                    product_name=product_name,
                    notification_type=notification.notification_type,
                    reference_date=notification.reference_date,
                    trigger_days_before=notification.trigger_days_before,
                    scheduled_at=notification.scheduled_at,
                    created_at=notification.created_at,
                    read_at=notification.read_at,
                )
                for notification, product_name in rows
            )
        except SQLAlchemyError as exc:
            raise NotificationPersistenceError from exc
        return NotificationPageRecord(items=items, total=total)

    def mark_read(
        self,
        *,
        user_id: UUID,
        notification_id: UUID,
        read_at: datetime,
    ) -> NotificationReadRecord | None:
        try:
            row = self._session.execute(
                update(Notification)
                .where(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,
                )
                .values(read_at=func.coalesce(Notification.read_at, read_at))
                .returning(Notification.id, Notification.read_at)
            ).one_or_none()
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise NotificationPersistenceError from exc
        if row is None:
            return None
        return NotificationReadRecord(id=row.id, read_at=row.read_at)
