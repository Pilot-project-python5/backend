from __future__ import annotations

import threading
from dataclasses import dataclass

import pytest

from yeongyangkkuk.worker.runtime import run_forever, run_once

pytestmark = pytest.mark.unit


@dataclass
class RecordingJob:
    calls: int = 0

    def run(self) -> None:
        self.calls += 1


def test_worker_runs_registered_job_once() -> None:
    job = RecordingJob()

    run_once(job)

    assert job.calls == 1


class StopAfterRunJob:
    def __init__(self, stop_event: threading.Event) -> None:
        self.stop_event = stop_event
        self.calls = 0

    def run(self) -> None:
        self.calls += 1
        self.stop_event.set()


def test_worker_loop_stops_after_signal() -> None:
    stop_event = threading.Event()
    job = StopAfterRunJob(stop_event)

    run_forever(job, interval_seconds=1, stop_event=stop_event)

    assert job.calls == 1
