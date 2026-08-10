"""기능 작업을 주기적으로 호출하는 교체 가능한 실행 루프."""

from __future__ import annotations

import logging
import threading
from typing import Protocol

from allyakkkuk.db.probe import DatabaseProbe

logger = logging.getLogger(__name__)


class WorkerJob(Protocol):
    def run(self) -> None: ...


class BootstrapWorkerJob:
    """기능 작업 등록 전 PostgreSQL 연결만 확인하는 부트스트랩 작업."""

    def __init__(self, probe: DatabaseProbe) -> None:
        self._probe = probe

    def run(self) -> None:
        self._probe.check()
        logger.info("작업자 준비 확인 완료; 등록된 알림 작업 없음")


def run_once(job: WorkerJob) -> None:
    job.run()


def run_forever(
    job: WorkerJob,
    *,
    interval_seconds: int,
    stop_event: threading.Event,
) -> None:
    while not stop_event.is_set():
        try:
            run_once(job)
        except Exception:
            logger.exception("작업자 실행 실패")
        stop_event.wait(interval_seconds)
