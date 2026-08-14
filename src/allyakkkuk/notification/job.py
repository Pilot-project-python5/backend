"""로컬 worker가 호출하는 재구매 알림 작업."""

from __future__ import annotations

import logging
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from allyakkkuk.notification.repository import (
    SQLAlchemyRepurchaseNotificationRepository,
)
from allyakkkuk.notification.service import RepurchaseNotificationService
from allyakkkuk.ports.clock import Clock

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
