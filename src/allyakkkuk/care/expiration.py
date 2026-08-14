"""구매분별 유통기한 D-day와 상태 계산."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

ExpirationStatus = Literal["NORMAL", "EXPIRING_SOON", "EXPIRED"]


@dataclass(frozen=True, slots=True)
class ExpirationState:
    days_until_expiration: int | None
    status: ExpirationStatus | None


def expiration_state(*, expiration_date: date | None, today: date) -> ExpirationState:
    if expiration_date is None:
        return ExpirationState(None, None)
    days = (expiration_date - today).days
    if days < 0:
        status: ExpirationStatus = "EXPIRED"
    elif days <= 5:
        status = "EXPIRING_SOON"
    else:
        status = "NORMAL"
    return ExpirationState(days, status)
