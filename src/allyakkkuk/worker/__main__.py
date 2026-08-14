"""로컬 작업자 프로세스 진입점."""

from __future__ import annotations

import signal
import threading
from zoneinfo import ZoneInfo

from allyakkkuk.core.config import get_settings
from allyakkkuk.core.logging import configure_logging
from allyakkkuk.db.session import SessionFactory
from allyakkkuk.notification.job import RepurchaseNotificationJob
from allyakkkuk.ports.clock import SystemClock
from allyakkkuk.worker.runtime import run_forever


def main() -> None:
    settings = get_settings()
    configure_logging(debug=settings.app_debug)
    stop_event = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    run_forever(
        RepurchaseNotificationJob(
            SessionFactory,
            SystemClock(),
            ZoneInfo(settings.app_timezone),
        ),
        interval_seconds=settings.worker_poll_seconds,
        stop_event=stop_event,
    )


if __name__ == "__main__":
    main()
