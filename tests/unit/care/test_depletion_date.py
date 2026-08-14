from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from allyakkkuk.care.depletion import (
    calculate_days_until_depletion,
    calculate_expected_depletion_date,
)

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.7")]


@pytest.mark.parametrize(
    ("total", "dose", "times", "expected"),
    [
        ("60", "1", 2, date(2026, 8, 30)),
        ("10", "1", 3, date(2026, 8, 4)),
        ("0.1", "0.1", 1, date(2026, 8, 1)),
        ("999999999.999", "0.001", 24, None),
    ],
)
def test_calculates_last_planned_day_with_partial_final_day(
    total: str,
    dose: str,
    times: int,
    expected: date | None,
) -> None:
    if expected is None:
        with pytest.raises(OverflowError):
            calculate_expected_depletion_date(
                intake_start_date=date(2026, 8, 1),
                total_quantity=Decimal(total),
                dose_per_intake=Decimal(dose),
                intakes_per_day=times,
            )
        return

    assert (
        calculate_expected_depletion_date(
            intake_start_date=date(2026, 8, 1),
            total_quantity=Decimal(total),
            dose_per_intake=Decimal(dose),
            intakes_per_day=times,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 8, 27), 3),
        (date(2026, 8, 30), 0),
        (date(2026, 8, 31), -1),
    ],
)
def test_calculates_signed_days_until_depletion(today: date, expected: int) -> None:
    assert (
        calculate_days_until_depletion(
            expected_depletion_date=date(2026, 8, 30),
            today=today,
        )
        == expected
    )
