"""로컬 작업자 프로세스 진입점."""

from __future__ import annotations

import signal
import threading
from zoneinfo import ZoneInfo

from yeongyangkkuk.adapters.email import SmtpEmailSender
from yeongyangkkuk.core.config import get_settings
from yeongyangkkuk.core.logging import configure_logging
from yeongyangkkuk.db.session import SessionFactory
from yeongyangkkuk.notification.job import NotificationJob
from yeongyangkkuk.ports.clock import SystemClock
from yeongyangkkuk.worker.runtime import run_forever


def main() -> None:
    settings = get_settings()
    configure_logging(debug=settings.app_debug)
    stop_event = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    run_forever(
        NotificationJob(
            SessionFactory,
            SystemClock(),
            ZoneInfo(settings.app_timezone),
            SmtpEmailSender(
                host=settings.mail_host,
                port=settings.mail_port,
                from_address=settings.mail_from_address,
                from_name=settings.mail_from_name,
            ),
        ),
        interval_seconds=settings.worker_poll_seconds,
        stop_event=stop_event,
    )


if __name__ == "__main__":
    main()
