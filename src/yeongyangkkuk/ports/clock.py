"""운영 시계와 결정적 테스트 시계."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FakeClock:
    def __init__(self, current: datetime) -> None:
        if current.tzinfo is None:
            raise ValueError("FakeClock은 시간대가 있는 일시가 필요합니다")
        self._current = current

    def now(self) -> datetime:
        return self._current

    def advance(self, delta: timedelta) -> None:
        self._current += delta
