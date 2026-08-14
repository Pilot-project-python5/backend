"""복용 계획의 예상 소진일과 D-day 계산."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_CEILING, Decimal


def calculate_expected_depletion_date(
    *,
    intake_start_date: date,
    total_quantity: Decimal,
    dose_per_intake: Decimal,
    intakes_per_day: int,
) -> date:
    daily_quantity = dose_per_intake * intakes_per_day
    if total_quantity <= 0 or daily_quantity <= 0:
        raise ValueError("총수량과 일일 사용량은 0보다 커야 합니다.")
    required_days = int(
        (total_quantity / daily_quantity).to_integral_value(rounding=ROUND_CEILING)
    )
    return intake_start_date + timedelta(days=required_days - 1)


def calculate_days_until_depletion(
    *, expected_depletion_date: date, today: date
) -> int:
    return (expected_depletion_date - today).days
