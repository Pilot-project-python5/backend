"""기능 작업을 주기적으로 호출하는 교체 가능한 실행 루프."""

from __future__ import annotations

import logging
import threading
from typing import Protocol

logger = logging.getLogger(__name__)


class WorkerJob(Protocol):
    def run(self) -> None: ...


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
