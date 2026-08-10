"""로컬 작업자 프로세스 진입점."""

from __future__ import annotations

import signal
import threading

from allyakkkuk.core.config import get_settings
from allyakkkuk.core.logging import configure_logging
from allyakkkuk.db.probe import SQLAlchemyDatabaseProbe
from allyakkkuk.db.session import engine
from allyakkkuk.worker.runtime import BootstrapWorkerJob, run_forever


def main() -> None:
    settings = get_settings()
    configure_logging(debug=settings.app_debug)
    stop_event = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    run_forever(
        BootstrapWorkerJob(SQLAlchemyDatabaseProbe(engine)),
        interval_seconds=settings.worker_poll_seconds,
        stop_event=stop_event,
    )


if __name__ == "__main__":
    main()
