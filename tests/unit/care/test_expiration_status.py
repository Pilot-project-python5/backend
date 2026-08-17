from datetime import date

import pytest

from yeongyangkkuk.care.expiration import expiration_state

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.11")]


@pytest.mark.parametrize(
    ("expiration_date", "today", "expected_days", "expected_status"),
    [
        (None, date(2026, 8, 14), None, None),
        (date(2026, 8, 20), date(2026, 8, 14), 6, "NORMAL"),
        (date(2026, 8, 19), date(2026, 8, 14), 5, "EXPIRING_SOON"),
        (date(2026, 8, 14), date(2026, 8, 14), 0, "EXPIRING_SOON"),
        (date(2026, 8, 13), date(2026, 8, 14), -1, "EXPIRED"),
    ],
)
def test_expiration_state_boundaries(
    expiration_date: date | None,
    today: date,
    expected_days: int | None,
    expected_status: str | None,
) -> None:
    result = expiration_state(expiration_date=expiration_date, today=today)

    assert result.days_until_expiration == expected_days
    assert result.status == expected_status
