"""로컬 worker가 호출하는 논리 알림 작업."""

from __future__ import annotations

import logging
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from yeongyangkkuk.notification.email_repository import (
    SQLAlchemyEmailDeliveryRepository,
)
from yeongyangkkuk.notification.email_service import EmailReminderService
from yeongyangkkuk.notification.repository import (
    SQLAlchemyExpirationNotificationRepository,
    SQLAlchemyRepurchaseNotificationRepository,
)
from yeongyangkkuk.notification.service import (
    ExpirationNotificationService,
    RepurchaseNotificationService,
)
from yeongyangkkuk.ports.clock import Clock
from yeongyangkkuk.ports.email import EmailSender

logger = logging.getLogger(__name__)


class SessionFactory(Protocol):
    def __call__(self) -> Session: ...


class RepurchaseNotificationJob:
    def __init__(
        self,
        session_factory: SessionFactory,
        clock: Clock,
        time_zone: ZoneInfo,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock
        self._time_zone = time_zone

    def run(self) -> None:
        with self._session_factory() as session:
            created = RepurchaseNotificationService(
                SQLAlchemyRepurchaseNotificationRepository(session),
                self._clock,
                self._time_zone,
            ).run()
        logger.info("재구매 논리 알림 작업 완료 created=%d", created)


class NotificationJob:
    def __init__(
        self,
        session_factory: SessionFactory,
        clock: Clock,
        time_zone: ZoneInfo,
        email_sender: EmailSender | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock
        self._time_zone = time_zone
        self._email_sender = email_sender

    def run(self) -> None:
        with self._session_factory() as session:
            repurchase_created = RepurchaseNotificationService(
                SQLAlchemyRepurchaseNotificationRepository(session),
                self._clock,
                self._time_zone,
            ).run()
            expiration_created = ExpirationNotificationService(
                SQLAlchemyExpirationNotificationRepository(session),
                self._clock,
                self._time_zone,
            ).run()
            email_summary = (
                EmailReminderService(
                    SQLAlchemyEmailDeliveryRepository(session),
                    self._email_sender,
                    self._clock,
                    self._time_zone,
                ).run()
                if self._email_sender is not None
                else None
            )
        logger.info(
            "논리 알림 작업 완료 repurchase_created=%d expiration_created=%d",
            repurchase_created,
            expiration_created,
        )
        if email_summary is not None:
            logger.info(
                "이메일 리마인더 작업 완료 enqueued=%d sent=%d retry=%d failed=%d",
                email_summary.enqueued,
                email_summary.sent,
                email_summary.retry_scheduled,
                email_summary.failed,
            )
