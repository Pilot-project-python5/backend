from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from allyakkkuk.ports.clock import FakeClock, SystemClock

pytestmark = pytest.mark.unit


def test_fake_clock_advances_deterministically() -> None:
    initial = datetime(2026, 8, 10, 0, 0, tzinfo=UTC)
    clock = FakeClock(initial)

    clock.advance(timedelta(minutes=10))

    assert clock.now() == initial + timedelta(minutes=10)


def test_fake_clock_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError):
        FakeClock(datetime(2026, 8, 10))


def test_system_clock_returns_utc_datetime() -> None:
    assert SystemClock().now().tzinfo is UTC
