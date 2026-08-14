"""재구매 논리 알림 저장소 포트와 PostgreSQL 구현."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from allyakkkuk.care.models import CareItem
from allyakkkuk.notification.models import Notification


class NotificationPersistenceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class RepurchaseTrigger:
    days_before: int
    reference_date: date


class RepurchaseNotificationRepository(Protocol):
    def create_repurchase_notifications(
        self,
        *,
        triggers: tuple[RepurchaseTrigger, ...],
        scheduled_at: datetime,
        created_at: datetime,
    ) -> int: ...


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
